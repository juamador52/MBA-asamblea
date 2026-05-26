import random
import numpy as np
import pandas as pd
import mesa

# ═══════════════════════════════════════════════════════════════
# PARAMETROS
# ═══════════════════════════════════════════════════════════════

DT = 0.01
ESCENARIO= "uniforme" #"uniforme" "polarizado" "fragmentado"

AFORO_MAXIMO = 100
TIEMPO_MAXIMO = 240

INTERVENCIONES_POR_VOTACION = 10
TIEMPO_VOTACION = 3

MIN_ESTUDIANTES = 5
ESTUDIANTES_INICIALES = 60

TASA_LLEGADAS = 1 / 3

TASA_SALIDA = 1 / 165

APERTURA_DIALOGO = 0.4
UMBRAL_IDEOLOGICO = 0.5

ALCANCE_INTERVENCION = 0.65

ESTANCAMIENTO_INICIAL = 1
AUMENTO_ESTANCAMIENTO = 0.2

LIMITES_VOTACION = (0.4, 0.6)

FACTOR_POLARIZACION = 2

EN_DEBATE = "En debate"
APROBADA = "Aprobada"
NEGADA = "Negada"

# ═══════════════════════════════════════════════════════════════
# AGENTE
# ═══════════════════════════════════════════════════════════════

class Estudiante(mesa.Agent):

    def __init__(self, unique_id, model, tiempo_llegada=0, escenario=ESCENARIO):

        super().__init__(unique_id, model)

        self.postura = self._postura_inicial(escenario)
        self.postura_inicial = self.postura

        self.persuasion = random.uniform(0, 1)

        self.tolerancia = self._tolerancia_inicial()
        self.tolerancia_inicial = self.tolerancia

        self.tiempo_llegada = tiempo_llegada
        self.tiempo_salida = np.nan

        self.activo = True

        self.tiempo_intervencion = 0

    # ═══════════════════════════════════════════════════════════

    def _tolerancia_inicial(self):

        dist = "exponencial"

        if dist == "exponencial":
            return np.random.exponential(1 / TASA_SALIDA)

        elif dist == "weibull":
            alpha = 1 / TASA_SALIDA
            beta = 2.0
            return alpha * np.random.weibull(beta)

        elif dist == "lognormal":
            mu = np.log(1 / TASA_SALIDA)
            sigma = 0.8
            return np.random.lognormal(mu, sigma)

    # ═══════════════════════════════════════════════════════════

    def _postura_inicial(self, escenario):

        if escenario == "polarizado":

            return random.choice([
                random.uniform(0.0, 0.25),
                random.uniform(0.75, 1.0)
            ])

        elif escenario == "fragmentado":

            return random.choice([
                random.uniform(0.0, 0.20),
                random.uniform(0.40, 0.60),
                random.uniform(0.80, 1.00)
            ])

        return random.uniform(0, 1)

# ═══════════════════════════════════════════════════════════════
# MODELO
# ═══════════════════════════════════════════════════════════════

class Asamblea(mesa.Model):

    def __init__(self):

        super().__init__()

        self.t = 0

        self.contador_ids = 0

        self.estudiantes = []

        self.numero_intervenciones = 0

        self.id_propuesta = 1

        self.estancamiento = ESTANCAMIENTO_INICIAL

        self.inicio_propuesta = 0

        self.ultima_fase = "intervencion"

        self.proxima_llegada = round(np.random.exponential(scale=1 / TASA_LLEGADAS), 2)

        self.intervencion_actual = None

        self.votacion_actual = None

        self.cerrado = False
        self.proximo_registro = 0
        self.DT_REGISTRO = 0.25

        self.df_intervenciones = pd.DataFrame(columns=[
            "ID Orador",
            "Inicio",
            "Fin",
            "Duracion",
            "Presentes Inicio",
            "Influidos Inicio",
            "Influidos Final",
            "Promedio Inicial",
            "Promedio Final"
        ])

        self.df_votaciones = pd.DataFrame(columns=[
            "ID Propuesta",
            "Inicio",
            "Fin",
            "Participantes",
            "Quorum",
            "SI",
            "NO",
            "ABSTENCION",
            "Resultado"
        ])

        self.df_tiempo = pd.DataFrame(columns=[
            "Tiempo",
            "Presentes",
            "Promedio Postura",
            "Desviacion Postura",
            "Quorum"
        ])

        for _ in range(ESTUDIANTES_INICIALES):
            self.crear_estudiante(0)

    # ═══════════════════════════════════════════════════════════

    def activos(self):
        return [e for e in self.estudiantes if e.activo]

    # ═══════════════════════════════════════════════════════════

    def crear_estudiante(self, tiempo):

        estudiante = Estudiante(self.contador_ids, self, tiempo)

        self.estudiantes.append(estudiante)

        self.contador_ids += 1

        return estudiante

    # ═══════════════════════════════════════════════════════════
    # LLEGADAS
    # ═══════════════════════════════════════════════════════════

    def manejar_llegadas(self):

        while self.t >= self.proxima_llegada and len(self.activos()) < AFORO_MAXIMO:

            nuevo = self.crear_estudiante(self.proxima_llegada)

            if self.votacion_actual is not None:
                self.votacion_actual["participantes"].add(nuevo)

            self.proxima_llegada = round(
                self.proxima_llegada + np.random.exponential(scale=1 / TASA_LLEGADAS),
                2
            )

    # ═══════════════════════════════════════════════════════════
    # DESGASTE
    # ═══════════════════════════════════════════════════════════

    def desgaste_continuo(self):

        presentes = self.activos()

        if len(presentes) == 0:
            return

        desviacion = np.std([e.postura for e in presentes])

        for e in presentes:

            polarizacion = 1

            if self.intervencion_actual is not None:

                orador = self.intervencion_actual["orador"]

                diferencia = abs(orador.postura - e.postura)

                polarizacion += FACTOR_POLARIZACION * diferencia * desviacion

            desgaste = DT * self.estancamiento * polarizacion

            e.tolerancia -= desgaste

            if e.tolerancia <= 0:

                e.activo = False

                e.tolerancia = 0

                e.tiempo_salida = round(self.t, 2)

    # ═══════════════════════════════════════════════════════════
    # INTERVENCIONES
    # ═══════════════════════════════════════════════════════════

    def iniciar_intervencion(self):

        if self.intervencion_actual is not None or self.votacion_actual is not None:
            return

        presentes = self.activos()

        if len(presentes) < MIN_ESTUDIANTES:
            return

        orador = random.choice(presentes)

        duracion = random.randint(2, 7)

        inicio = round(self.t, 2)

        fin = round(inicio + duracion, 2)

        audiencia_inicial = [
            e for e in presentes
            if e != orador and random.random() < ALCANCE_INTERVENCION
        ]

        self.intervencion_actual = {
            "orador": orador,
            "inicio": inicio,
            "fin": fin,
            "duracion": duracion,
            "presentes_inicio": len(presentes),
            "audiencia_inicial": audiencia_inicial
        }

# ═══════════════════════════════════════════════════════════

    def finalizar_intervencion(self):

        datos = self.intervencion_actual

        if datos is None:
            return

        if round(self.t, 2) < datos["fin"]:
            return

        orador = datos["orador"]

        audiencia_inicial = datos["audiencia_inicial"]

        sobrevivientes = [e for e in audiencia_inicial if e.activo]

        promedio_inicial = np.mean([e.postura for e in audiencia_inicial]) if len(audiencia_inicial) > 0 else np.nan

        promedio_final = np.nan

        if len(sobrevivientes) > 0:

            desviacion = np.std([e.postura for e in sobrevivientes])

            for e in sobrevivientes:

                diferencia = abs(orador.postura - e.postura)

                cambio = orador.persuasion * (orador.postura - e.postura) * np.exp(-diferencia / APERTURA_DIALOGO)

                polarizacion = 1 + FACTOR_POLARIZACION * diferencia * desviacion

                cambio *= polarizacion

                if diferencia <= UMBRAL_IDEOLOGICO:
                    e.postura += cambio
                else:
                    e.postura -= cambio

                e.postura = max(0, min(1, e.postura))

            promedio_final = np.mean([e.postura for e in sobrevivientes])

        orador.tiempo_intervencion += datos["duracion"]

        self.numero_intervenciones += 1

        self.df_intervenciones.loc[len(self.df_intervenciones)] = {
            "ID Orador": orador.unique_id,
            "Inicio": datos["inicio"],
            "Fin": datos["fin"],
            "Duracion": datos["duracion"],
            "Presentes Inicio": datos["presentes_inicio"],
            "Influidos Inicio": len(audiencia_inicial),
            "Influidos Final": len(sobrevivientes),
            "Promedio Inicial": promedio_inicial,
            "Promedio Final": promedio_final
        }

        self.intervencion_actual = None

    # ═══════════════════════════════════════════════════════════
    # VOTACIONES
    # ═══════════════════════════════════════════════════════════

    def iniciar_votacion(self):

        if self.votacion_actual is not None or self.intervencion_actual is not None:
            return

        inicio = round(self.t, 2)

        fin = round(inicio + TIEMPO_VOTACION, 2)

        participantes = set(self.activos())

        self.votacion_actual = {
            "inicio": inicio,
            "fin": fin,
            "participantes": participantes
        }

    # ═══════════════════════════════════════════════════════════

    def finalizar_votacion(self):

        datos = self.votacion_actual

        if datos is None:
            return

        if round(self.t, 2) < datos["fin"]:
            return

        participantes = list(datos["participantes"])

        quorum = (len(participantes) // 2) + 1

        votos_si = 0
        votos_no = 0
        abstenciones = 0

        limite_no, limite_si = LIMITES_VOTACION

        for e in participantes:

            if e.postura >= limite_si:
                votos_si += 1

            elif e.postura <= limite_no:
                votos_no += 1

            else:
                abstenciones += 1

        resultado = EN_DEBATE

        if votos_si >= quorum:
            resultado = APROBADA

        elif votos_no >= quorum:
            resultado = NEGADA

        self.df_votaciones.loc[len(self.df_votaciones)] = {
            "ID Propuesta": self.id_propuesta,
            "Inicio": datos["inicio"],
            "Fin": datos["fin"],
            "Participantes": len(participantes),
            "Quorum": quorum,
            "SI": votos_si,
            "NO": votos_no,
            "ABSTENCION": abstenciones,
            "Resultado": resultado
        }

        if resultado == EN_DEBATE:

            self.estancamiento *= (1 + AUMENTO_ESTANCAMIENTO)

        else:

            self.id_propuesta += 1

            self.estancamiento = ESTANCAMIENTO_INICIAL

            self.inicio_propuesta = self.t

        self.votacion_actual = None

    def recolectar_datos(self):
        presentes = self.activos()
        if len(presentes) == 0:
            return
        posturas = [e.postura for e in presentes]
        promedio = np.mean(posturas)
        desviacion = np.std(posturas)
        quorum = (len(presentes) // 2) + 1
        self.df_tiempo.loc[len(self.df_tiempo)] = {
            "Tiempo": round(self.t, 2),
            "Presentes": len(presentes),
            "Promedio Postura": promedio,
            "Desviacion Postura": desviacion,
            "Quorum": quorum}

    # ═══════════════════════════════════════════════════════════
    # STEP
    # ═══════════════════════════════════════════════════════════

    def step(self):

        self.manejar_llegadas()

        self.desgaste_continuo()

        self.finalizar_intervencion()

        self.finalizar_votacion()

        if not self.cerrado:

            if self.intervencion_actual is None and self.votacion_actual is None:

                if (
                    self.numero_intervenciones > 0
                    and
                    self.numero_intervenciones % INTERVENCIONES_POR_VOTACION == 0
                    and
                    self.ultima_fase != "votacion"
                ):

                    self.iniciar_votacion()

                    self.ultima_fase = "votacion"

                else:

                    self.iniciar_intervencion()

                    self.ultima_fase = "intervencion"

        if self.t >= self.proximo_registro:
            self.recolectar_datos()
            self.proximo_registro = round(self.proximo_registro + self.DT_REGISTRO,2)
        self.t = round(self.t + DT, 2)
    # ═══════════════════════════════════════════════════════════

    def run_model(self):

        while self.t < TIEMPO_MAXIMO:

            self.step()

        self.cerrado = True

        # CONTINUAR HASTA TERMINAR
        # INTERVENCION/VOTACION ACTIVA

        while (self.intervencion_actual is not None or self.votacion_actual is not None):
            self.step()

        # VOTACION FINAL
        # SI QUEDARON INTERVENCIONES

        if ( self.numero_intervenciones > 0 and self.numero_intervenciones % INTERVENCIONES_POR_VOTACION != 0 ):

            self.iniciar_votacion()

            while self.votacion_actual is not None:

                self.step()

        self.resultados()

    # ═══════════════════════════════════════════════════════════

    def resultados(self):

        df_estudiantes = pd.DataFrame([{
            "ID": e.unique_id,
            "Postura Inicial": round(e.postura_inicial, 4),
            "Postura Final": round(e.postura, 4),
            "Persuasion": round(e.persuasion, 4),
            "Tolerancia Inicial": round(e.tolerancia_inicial, 2),
            "Tolerancia Final": round(e.tolerancia, 2),
            "Tiempo Llegada": round(e.tiempo_llegada, 2),
            "Tiempo Salida": e.tiempo_salida,
            "Tiempo Intervencion": round(e.tiempo_intervencion, 2),
            "Activo": e.activo
        } for e in self.estudiantes])

        print("\nINTERVENCIONES\n")
        print(self.df_intervenciones)

        print("\nVOTACIONES\n")
        print(self.df_votaciones)

        print("\nESTUDIANTES\n")
        print(df_estudiantes)

        print("\nTiempo Final:", round(self.t, 2))
        print("Intervenciones:", self.numero_intervenciones)
        print("Propuestas aprobadas:", self.id_propuesta - 1)
        print("Presentes:", len(self.activos()))
        print("Total estudiantes:", len(self.estudiantes))
        print(self.df_tiempo)

def n_run(n=50):

        acuerdos = []

        for i in range(n):

            modelo = Asamblea()

            modelo.run_model()

            total_acuerdos = modelo.id_propuesta - 1

            acuerdos.append(total_acuerdos)

        categorias = {
            "0": 0,
            "1": 0,
            "2": 0,
            "3": 0,
            "4": 0,
            "5+": 0
        }

        for a in acuerdos:

            if a == 0:
                categorias["0"] += 1

            elif a == 1:
                categorias["1"] += 1

            elif a == 2:
                categorias["2"] += 1

            elif a == 3:
                categorias["3"] += 1

            elif a == 4:
                categorias["4"] += 1

            else:
                categorias["5+"] += 1

        resultados = []

        z = 1.96

        for categoria, frecuencia in categorias.items():

            p = frecuencia / n

            error = z * np.sqrt((p * (1 - p)) / n)

            li = max(0, p - error)

            ls = min(1, p + error)

            resultados.append({
                "Acuerdos": categoria,
                "Frecuencia": frecuencia,
                "Probabilidad": p,
                "IC 95% Inferior": li,
                "IC 95% Superior": ls
            })

        df_resultados = pd.DataFrame(resultados)

        print("\nRESULTADOS N RUN\n")
        print(resultados)
        print(df_resultados)
        print(acuerdos)

        return df_resultados

# ═══════════════════════════════════════════════════════════════
# EJECUCION
# ═══════════════════════════════════════════════════════════════

modelo = Asamblea()
#n_run(1000)
modelo.run_model()