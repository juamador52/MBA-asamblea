"""
===============================================================================
SIMULACION BASADA EN AGENTES DE UNA ASAMBLEA ESTUDIANTIL
===============================================================================
DESCRIPCION

Este script implementa un modelo basado en agentes para simular la dinamica 
de una asamblea estudiantil bajo distintos escenarios ideologicos y sociales.
La simulacion representa un espacio donde los estudiantes ingresan,
participan en intervenciones, modifican sus posturas ideologicas y participan 
en votaciones para decidir sobre una propuesta.

El modelo busca analizar propiedades emergentes como:
    - consenso
    - polarizacion
    - probabilidad de alcanzar acuerdos

Al iniciar la simulacion se crean N = ESTUDIANTES_INICIALES.
Cada estudiante recibe aleatoriamente:
    - una postura ideologica inicial
    - una capacidad de persuasion
    - una tolerancia social inicial

La distribucion de posturas depende del escenario seleccionado, el cual 
puede ser:
    - uniforme
    - polarizado
    - fragmentado

Durante la simulacion pueden llegar nuevos estudiantes, donde
los tiempos entre llegadas siguen una distribucion exponencial, las 
llegadas son independientes y la tasa de llegada es constante

El numero de estudiantes nunca puede superar AFORO_MAXIMO.

La asamblea evoluciona mediante intervenciones sucesivas.

En cada intervencion:
    - se selecciona un orador aleatorio
    - se define una duracion aleatoria
    - un subconjunto de los presentes puede ser influenciado

El cambio de postura depende de:
    - persuasion del orador
    - diferencia ideologica
    - apertura al dialogo
    - polarizacion del entorno

Los agentes cercanos ideologicamente tienden a converger,
mientras que agentes muy alejados pueden radicalizarse.

Todos los estudiantes sufren desgaste continuo mientras permanecen
en la asamblea.

El desgaste aumenta debido a:
    - estancamiento en las votaciones
    - polarizacion percibida 

Cuando la tolerancia de un estudiante llega a cero 
abandona la asamblea

Despues de un numero fijo de intervenciones se realiza una votacion.

Cada estudiante vota segun su postura por:
    - SI
    - NO
    - ABSTENCION

Para aprobar o negar una propuesta se requiere quorum:
    quorum = (N // 2) + 1 donde N es la cantidad de estudiantes presentes

Si no se logra un acuerdo:
    - la propuesta permanece EN_DEBATE
    - aumenta el estancamiento

La simulacion principal termina cuando:
    t >= TIEMPO_MAXIMO

Sin embargo, el modelo realiza un cierre controlado:
    - las intervenciones activas finalizan
    - las votaciones pendientes concluyen
    - si quedan intervenciones sin votacion asociada,
      se ejecuta una votacion final

Esto evita procesos truncados.
===============================================================================
EJECUCION DEL MODELO

1. EJECUCION SIMPLE
    Para ejecutar una simulacion individual:
        modelo = Asamblea()
        modelo.run_model()

2. MULTIPLES EJECUCIONES
    Para ejecutar varias simulaciones independientes:
        n_run(50)
    Esto permite estimar la probabilidad de alcanzar al menos un acuerdo
===============================================================================
CONFIGURACION DEL ESCENARIO

El escenario inicial puede modificarse desde:

    ESCENARIO = "uniforme"

Opciones disponibles:
    - "uniforme"
    - "polarizado"
    - "fragmentado"
===============================================================================
Autores:
    Juan David Amado Rubio - juamador@unal.edu.co
    Brandon Losada Socha - blosadas@unal.edu.co 
    Víctor Camilo Cañón Castellanos - vcanonc@unal.edu.co
===============================================================================
Curso:
    Modelos y simulación (2025970-4)
===============================================================================
Fecha:
    27-05-2026
"""

import random
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# PARAMETROS
DT = 0.01
ESCENARIO =  "fragmentado" # "uniforme" "polarizado" "fragmentado"

AFORO_MAXIMO = 200
TIEMPO_MAXIMO = 120

INTERVENCIONES_POR_VOTACION = 15
TIEMPO_VOTACION = 3

MIN_ESTUDIANTES = 20
ESTUDIANTES_INICIALES = 140

MEDIA_LLEGADAS = 3 
MEDIA_SALIDA = 100  

APERTURA_DIALOGO = 0.55
UMBRAL_IDEOLOGICO = 0.6

#Duracion de intervenciones
MEDIA_DURACION = 4
DESV_DURACION = 2

ESTANCAMIENTO_INICIAL = 1
AUMENTO_ESTANCAMIENTO = 0.20

LIMITES_VOTACION = (0.42, 0.58)

FACTOR_PERCEPCION = 1.5

EN_DEBATE = "En debate"
APROBADA = "Aprobada"
NEGADA = "Negada"

# AGENTE
class Estudiante:

    def __init__(self, unique_id, model, tiempo_llegada=0, escenario=ESCENARIO):

        self.unique_id = unique_id
        self.model = model

        self.postura = self._postura_inicial(escenario)
        self.postura_inicial = self.postura

        self.persuasion = random.uniform(0, 1)

        self.tolerancia = self._tolerancia_inicial()
        self.tolerancia_inicial = self.tolerancia

        self.tiempo_llegada = tiempo_llegada
        self.tiempo_salida = np.nan

        self.activo = True

        self.tiempo_intervencion = 0

    def _tolerancia_inicial(self):
        """
        Genera la tolerancia inicial del estudiante utilizando
        una distribucion probabilistica.

        La tolerancia modela el tiempo de permanencia del agente
        dentro de la asamblea antes de abandonar el sistema
        por el desgaste.

        Actualmente se utiliza una distribucion exponencial
        Tambien se incluyen alternativas como Weibull y Lognormal, para
        cambiar la opcion se debe editar dist por:
            "exponencial"
            "weibull"
            "lognormal"

        Return:
            float
                Valor inicial de tolerancia del estudiante
        """
        dist = "exponencial"
        if dist == "exponencial":
            return np.random.exponential(MEDIA_SALIDA)

        elif dist == "weibull":
            alpha = MEDIA_SALIDA #ESCALA
            beta = 2.0
            return alpha * np.random.weibull(beta)

        elif dist == "lognormal":
            mu = np.log(MEDIA_SALIDA)
            sigma = 0.8
            return np.random.lognormal(mu, sigma)

    def _postura_inicial(self, escenario):
        """
        Genera la postura ideologica inicial del estudiante
        segun el escenario seleccionado.

        Escenario uniforme:
            - opiniones distribuidas en todo el espectro ideologico
        Escenario polarizado:
            - concentracion en extremos ideologicos
        Escenario fragmentado:
            - multiples grupos ideologicos separados

        Parametros:
            escenario : str
                Tipo de distribucion ideologica inicial

        Return:
            float
                Valor de postura ideologica entre 0 y 1.
        """
        if escenario == "polarizado":

            return random.choice([
                random.uniform(0, 0.25),
                random.uniform(0.75, 1)
            ])

        elif escenario == "fragmentado":

            return random.choice([
                random.uniform(0.0, 0.20),
                random.uniform(0.45, 0.55),
                random.uniform(0.8, 1)
            ])

        return random.uniform(0, 1)

#MODELO
class Asamblea:
    """
    Modelo principal de simulacion de la asamblea estudiantil
    Gestiona:
        - agentes
        - intervenciones
        - votaciones
        - procesos de llegada y salida
        - recoleccion de datos
        - paso del tiempo del sistema
    """

    def __init__(self):
        """
        Inicializa el modelo de asamblea.

        Se crean:
            - variables globales del sistema
            - estructuras de almacenamiento
            - dataframes de resultados
            - estudiantes iniciales
        """
        self.t = 0
        self.contador_ids = 0
        self.estudiantes = []
        self.numero_intervenciones = 0
        self.id_propuesta = 1
        self.estancamiento = ESTANCAMIENTO_INICIAL
        self.inicio_propuesta = 0
        self.ultima_fase = "intervencion"
        self.proxima_llegada = round(np.random.exponential(MEDIA_LLEGADAS), 3)

        self.intervencion_actual = None

        self.votacion_actual = None

        self.cerrado = False

        self.proximo_registro = 0

        self.DT_REGISTRO = 0.5

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
            "Desviación Postura",
            "Quorum",
            "Apoyo SI",
            "Apoyo NO"
        ])

        for _ in range(ESTUDIANTES_INICIALES):
            self.crear_estudiante(0)


    def activos(self):
        """
        Obtiene la lista de estudiantes activos.

        Returns
            list
                Lista de estudiantes presentes en la asamblea.
        """
        return [e for e in self.estudiantes if e.activo]


    def crear_estudiante(self, tiempo):
        """
        Crea un nuevo estudiante y lo agrega al modelo.

        Parametros:
            tiempo : float
                Tiempo de llegada del estudiante.

        Returns
            Estudiante
                Nuevo agente creado.
        """
        estudiante = Estudiante(
            self.contador_ids,
            self,
            tiempo
        )

        self.estudiantes.append(estudiante)

        self.contador_ids += 1

        return estudiante

    def manejar_llegadas(self):
        """
        Gestiona la llegada de nuevos estudiantes al sistema.

        Los tiempos entre llegadas siguen una distribucion
        exponencial y las llegadas se mantienen mientras
        no se supere el AFORO_MAXIMO.
        """
        while (
            self.t >= self.proxima_llegada
            and
            len(self.activos()) < AFORO_MAXIMO
        ):

            nuevo = self.crear_estudiante(self.proxima_llegada)

            if self.votacion_actual is not None:
                self.votacion_actual["participantes"].add(nuevo)

            self.proxima_llegada = round(
                self.proxima_llegada +
                np.random.exponential(MEDIA_LLEGADAS),3)

    def desgaste_continuo(self):
        """
        Aplica un desgaste continuo a los estudiantes activos.

        El desgaste depende de:
            - estancamiento
            - dispersion de posturas ideologicas
            - diferencia de posturas respecto al orador actual

        Cuando la tolerancia llega a cero,
        el estudiante abandona la asamblea.
        """
        presentes = self.activos()

        if len(presentes) == 0:
            return

        desviacion = np.std([e.postura for e in presentes])

        for e in presentes:
            percepcion_polarizacion = 1

            if self.intervencion_actual is not None:
                orador = self.intervencion_actual["orador"]
                diferencia = abs(orador.postura - e.postura)
                percepcion_polarizacion += (
                    FACTOR_PERCEPCION *
                    diferencia *
                    desviacion)
                
            percepcion_polarizacion += (
                    FACTOR_PERCEPCION *
                    desviacion)

            desgaste = DT * self.estancamiento * percepcion_polarizacion
            e.tolerancia -= desgaste

            if e.tolerancia <= 0:
                e.activo = False
                e.tolerancia = 0
                e.tiempo_salida = round(self.t, 3)

    #======================================================================================
    #INTERVENCIONES


    def iniciar_intervencion(self):
        """
        Inicia una nueva intervencion dentro de la asamblea.

        Una intervencion representa un periodo de deliberacion donde
        un estudiante actua como orador e influye potencialmente
        sobre otros agentes presentes.

        Condiciones necesarias:
            - no debe existir una intervencion activa
            - no debe existir una votacion activa
            - el numero de estudiantes presentes > MIN_ESTUDIANTES 

        Proceso:
            1. se selecciona un orador aleatoriamente
            2. se genera una duracion aleatoria usando una
            distribucion normal
            3. se define el instante de inicio y finalizacion
            4. se selecciona una audiencia potencialmente influenciada

        La informacion de la intervencion se almacena en
        self.intervencion_actual para ser procesada posteriormente
        por finalizar_intervencion().
        """
        global MEDIA_DURACION
        global DESV_DURACION
        if (self.intervencion_actual is not None
            or self.votacion_actual is not None):
            return
        presentes = self.activos()
        if len(presentes) < MIN_ESTUDIANTES:
            return

        # El orador es seleccionado aletoriamente dentro de los
        # estudiantes que esten presentes
        orador = random.choice(presentes)

        # La duracion de la intervencion sigue una distribucion
        # normal donde:
        #    - MEDIA_DURACION controla la duracion promedio
        #    - DESV_DURACION representa la desviacion estandar
        # Se impone un minimo de 0.5 minutos para evitar
        # duraciones negativas o intervenciones instantaneas.
        duracion = round(max(0.5,random.gauss(MEDIA_DURACION, DESV_DURACION)),3)

        inicio = round(self.t, 3)
        fin = round(inicio + duracion, 3)

        # La audiencia se selecciona usando
        # la persuacion del orador, la cual representa la probabilidad
        # de que un estudiante escuche activamente al orador.
        audiencia_inicial = [
            e for e in presentes if (e != orador
                and random.random() < orador.persuasion)]

        self.intervencion_actual = {
            "orador": orador,
            "inicio": inicio,
            "fin": fin,
            "duracion": duracion,
            "presentes_inicio": len(presentes),
            "audiencia_inicial": audiencia_inicial
        }


    def finalizar_intervencion(self):
        """
        Finaliza la intervencion activa y actualiza las posturas de los
        estudiantes influenciados.

        Una vez terminada la intervencion:
            - se identifica el orador
            - se recupera la audiencia inicial
            - se filtran los estudiantes que permanecen activos

        El cambio de postura de cada estudiante influenciado y presente depende de:
            - la persuasion del orador
            - la diferencia ideologica entre ambos
            - la apertura al dialogo

        El cambio ideologico sigue una dinamica exponencial:
            cambio = persuasion * diferencia_postura *
                    exp(-diferencia / APERTURA_DIALOGO)

        Si la diferencia ideologica entre el orador y el estudiante es
        menor o igual al umbral ideologico:
            - el estudiante se aproxima a la postura del orador

        Si la diferencia supera el umbral:
            - el estudiante se aleja de la postura del orador
            - ocurre un efecto de radicalizacion

        Despues de actualizar las posturas:
            - los valores se limitan al intervalo [0, 1]
            - se calcula el promedio ideologico final
            - se registra la intervencion en el dataframe
            - se actualiza el tiempo acumulado del orador
            - se incrementa el contador de intervenciones

        Finalmente:
            - la intervencion activa se elimina
            - la asamblea queda disponible para una nueva fase
        """
        datos = self.intervencion_actual

        if datos is None:
            return
        
        if round(self.t, 3) < datos["fin"]:
            return

        orador = datos["orador"]
        audiencia_inicial = datos["audiencia_inicial"]
        sobrevivientes = [
            e for e in audiencia_inicial
            if e.activo]

        promedio_inicial = (
            np.mean([e.postura for e in audiencia_inicial])
            if len(audiencia_inicial) > 0
            else np.nan)

        promedio_final = np.nan

        if len(sobrevivientes) > 0:
            for e in sobrevivientes:

                diferencia = abs(
                    orador.postura - e.postura)

                cambio = (
                    orador.persuasion *
                    (orador.postura - e.postura) *
                    np.exp(-diferencia / APERTURA_DIALOGO) )

                if diferencia <= UMBRAL_IDEOLOGICO:
                    e.postura += cambio
                else:
                    e.postura -= cambio

                e.postura = max(0, min(1, e.postura))

            promedio_final = np.mean([
                e.postura for e in sobrevivientes
            ])

        orador.tiempo_intervencion += datos["duracion"]
        self.numero_intervenciones += 1
        self.df_intervenciones.loc[
            len(self.df_intervenciones)
        ] = {
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

    # =============================================================================================
    # VOTACIONES
    def iniciar_votacion(self):
        """
        Inicia una nueva votacion dentro de la asamblea.

        Una votacion solo puede comenzar cuando:
            - no existe una votacion activa
            - no existe una intervencion en curso

        Al iniciar la votacion:
            - se registra el tiempo de inicio
            - se calcula el instante de finalizacion
            - se almacenan todos los estudiantes activos
            como participantes potenciales

        Los participantes se almacenan en un conjunto para:
            - evitar duplicados
            - permitir la incorporacion de nuevos estudiantes
            que lleguen durante la votacion

        La votacion permanece activa hasta que:
            tiempo_actual >= fin
        """

        if (self.votacion_actual is not None
            or self.intervencion_actual is not None):
            return

        inicio = round(self.t, 3)

        fin = round(inicio + TIEMPO_VOTACION, 3)

        participantes = set(self.activos())

        self.votacion_actual = {
            "inicio": inicio,
            "fin": fin,
            "participantes": participantes }


    def finalizar_votacion(self):
        """
        Finaliza la votacion activa y determina el resultado
        de la propuesta actual.

        Al finalizar:
            - se recupera la lista de participantes
            - se calcula el quorum requerido
            - se cuentan los votos SI, NO y ABSTENCION

        Cada estudiante vota segun su postura ideologica:
            - postura >= limite_si      -> voto SI
            - postura <= limite_no      -> voto NO
            - valores intermedios       -> ABSTENCION

        Una propuesta se considera:
            - APROBADA si votos_si >= quorum
            - NEGADA si votos_no >= quorum
            - EN_DEBATE en cualquier otro caso

        Si la propuesta permanece EN_DEBATE:
            - aumenta el estancamiento de la asamblea
            - el desgaste futuro se intensifica

        Si se alcanza un acuerdo:
            - se incrementa el identificador de propuesta
            - el estancamiento vuelve al valor inicial
            - se actualiza el tiempo de inicio de propuesta

        Toda la informacion de la votacion se almacena en:
            self.df_votaciones

        Finalmente:
            - la votacion activa se elimina
            - la asamblea queda disponible para nuevas
            intervenciones o votaciones
        """
        datos = self.votacion_actual

        if datos is None:
            return

        if round(self.t, 3) < datos["fin"]:
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

        self.df_votaciones.loc[
            len(self.df_votaciones)
        ] = {
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

            self.estancamiento *= (
                1 + AUMENTO_ESTANCAMIENTO
            )

        else:

            self.id_propuesta += 1

            self.estancamiento = ESTANCAMIENTO_INICIAL

            self.inicio_propuesta = self.t

        self.votacion_actual = None

    # =============================================================================

    def recolectar_datos(self):
        """
        Recolecta informacion del sistema para un
        analisis posterior y visualizacion.

        Variables registradas:
            - tiempo actual
            - numero de estudiantes presentes
            - promedio ideologico
            - desviacion ideologica
            - quorum requerido

        Los datos son almacenados en self.df_tiempo
        y posteriormente utilizados para graficos
        y un analisis estadistico
        """
        presentes = self.activos()

        if len(presentes) == 0:
            return

        posturas = [e.postura for e in presentes]

        promedio = np.mean(posturas)

        desviacion = np.std(posturas)

        quorum = (len(presentes) // 2) + 1

        limite_no, limite_si = LIMITES_VOTACION

        apoyo_si = sum(
            e.postura >= limite_si
            for e in presentes
        )

        apoyo_no = sum(
            e.postura <= limite_no
            for e in presentes
        )

        self.df_tiempo.loc[
            len(self.df_tiempo)
        ] = {
            "Tiempo": round(self.t, 3),
            "Presentes": len(presentes),
            "Promedio Postura": promedio,
            "Desviación Postura": desviacion,
            "Quorum": quorum,
            "Apoyo SI": apoyo_si,
            "Apoyo NO": apoyo_no
        }

    # TICKS
    def step(self):
        """
        Ejecuta un paso de tiempo en la simulacion.

        Orden de ejecucion:
            1. gestionar llegadas de estudiantes
            2. aplicar desgaste continuo
            3. finalizar intervenciones activas
            4. finalizar votaciones activas
            5. iniciar nuevas fases
            6. recolectar datos
            7. avanzar el reloj de simulacion

        Dinamica de la asambela
            - despues de cierto numero de intervenciones
            se inicia una votacion
            - en caso contrario se inicia una nueva intervencion

        El modelo usa DT como unidad de avance

        La recoleccion de datos se realiza cada DT_REGISTRO

        El tiempo interno del sistema se actualiza mediante:
            t = t + DT
        """
        self.manejar_llegadas()

        self.desgaste_continuo()

        self.finalizar_intervencion()

        self.finalizar_votacion()

        if not self.cerrado:

            if (
                self.intervencion_actual is None
                and
                self.votacion_actual is None
            ):

                if (
                    self.numero_intervenciones > 0
                    and
                    self.numero_intervenciones %
                    INTERVENCIONES_POR_VOTACION == 0
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

            self.proximo_registro = round(
                self.proximo_registro +
                self.DT_REGISTRO,
                2
            )

        self.t = round(self.t + DT, 3)

    # ====================================================================

    def run_model(self, df=False, graficos=True, resumen=True):
        """
        Ejecuta la simulacion de la asamblea

        La simulacion se ejecuta hasta alcanzar:
            t >= TIEMPO_MAXIMO

        Al finalizar el tiempo maximo se realiza un
        cierre controlado del sistema.

        El cierre garantiza:
            - finalizar intervenciones pendientes
            - concluir votaciones activas
            - ejecutar una votacion final si es necesaria

        Parametros:
            df : bool, default=False
                Indica si se imprimen los dataframes generados.

            graficos : bool, default=True
                Indica si se generan graficas.

            resumen : bool, default=True
                Indica si se imprime un resumen estadistico.

        Return
            dict
                Diccionario con:
                    - dataframe de intervenciones
                    - dataframe de votaciones
                    - dataframe de estudiantes
                    - dataframe temporal
        """
        while self.t < TIEMPO_MAXIMO:
            self.step()

        self.cerrado = True

        while (
            self.intervencion_actual is not None
            or
            self.votacion_actual is not None
        ):
            self.step()

        if (
            self.numero_intervenciones > 0
            and
            self.numero_intervenciones % INTERVENCIONES_POR_VOTACION != 0
        ):

            self.iniciar_votacion()

            while self.votacion_actual is not None:
                self.step()

        return self.resultados(
            df=df,
            graficos=graficos,
            resumen=resumen
        )

    # ===========================================================================

    def resultados(self, df=False, graficos=True, resumen=True):
        """
        Construye, organiza y presenta los resultados finales
        de la simulacion.

        Informacion registrada por estudiante:
            - postura inicial y final
            - persuasion
            - tolerancia inicial y final
            - tiempo de llegada
            - tiempo de salida
            - tiempo acumulado de intervencion
            - estado final dentro del sistema

        Graficas generadas:
            1. Prostura promedio a lo largo del tiempo
            2. desviacion ideologica
            3. histogramas de postura inicial y final
            4. quorum a lo largo del tiempo
            5. Trayectoria temporal de opiniones

        Parametros
            df : bool, default=False
                Indica si se imprimen los dataframes.

            graficos : bool, default=True
                Indica si se generan figuras y visualizaciones.

            resumen : bool, default=True
                Indica si se imprime un resumen general.

        Return
            dict
                Diccionario con los principales dataframes
                generados por la simulacion.
        """

        df_estudiantes = pd.DataFrame([{
            "ID": e.unique_id,
            "Postura Inicial": round(e.postura_inicial, 4),
            "Postura Final": round(e.postura, 4),
            "Persuasion": round(e.persuasion, 4),
            "Tolerancia Inicial": round(e.tolerancia_inicial, 3),
            "Tolerancia Final": round(e.tolerancia, 3),
            "Tiempo Llegada": round(e.tiempo_llegada, 3),
            "Tiempo Salida": e.tiempo_salida,
            "Tiempo Intervencion": round(e.tiempo_intervencion, 3),
            "Activo": e.activo
        } for e in self.estudiantes])

        if df:

            print("\nINTERVENCIONES\n")
            print(self.df_intervenciones)

            print("\nVOTACIONES\n")
            print(self.df_votaciones)

            print("\nESTUDIANTES\n")
            print(df_estudiantes)

            print("\nDATOS TEMPORALES\n")
            print(self.df_tiempo)

        if resumen:

            print("\n" + "=" * 60)
            print("RESUMEN DE LA SIMULACIÓN")
            print("=" * 60)

            print(f"Escenario:                {ESCENARIO}")
            print(f"Tiempo final:             {round(self.t, 3)}")
            print(f"Intervenciones:           {self.numero_intervenciones}")
            print(f"Acuerdos logrados:        {self.id_propuesta - 1}")
            print(f"Estudiantes presentes:    {len(self.activos())}")
            print(f"Total estudiantes:        {len(self.estudiantes)}")

            print("=" * 60)

        if graficos:
            #datos
            tiempo = self.df_tiempo["Tiempo"]
            promedio = self.df_tiempo["Promedio Postura"]
            desviacion = self.df_tiempo["Desviación Postura"]
            quorum = self.df_tiempo["Quorum"]
            posturas_iniciales = df_estudiantes["Postura Inicial"]
            posturas_finales = df_estudiantes["Postura Final"]
            quorum_minimo = (MIN_ESTUDIANTES // 2) + 1
            limite_no, limite_si = LIMITES_VOTACION

            #estilo
            plt.rcParams.update({
                "axes.facecolor": "#FAFAFA",
                "figure.facecolor": "white",
                "axes.grid": True,
                "grid.alpha": 0.25,
                "grid.linestyle": "--",
                "font.size": 10
            })
            #=====================================================================
            #ventana 1, 4 graficos
            fig, axs = plt.subplots(2, 2, figsize=(14, 8))
            fig.suptitle(
                f"Escenario {ESCENARIO.upper()}",
                fontsize=18,
                fontweight="bold"
            )
            # zonas ideologicas
            axs[0, 0].axhspan(
                0,
                limite_no,
                alpha=0.08,
                color="#D32F2F"
            )

            axs[0, 0].axhspan(
                limite_no,
                limite_si,
                alpha=0.05,
                color="gray"
            )

            axs[0, 0].axhspan(
                limite_si,
                1,
                alpha=0.08,
                color="#2E7D32"
            )

            # curva principal
            axs[0, 0].plot(
                tiempo,
                promedio,
                color="#1565C0",
                linewidth=3,
                label="Media"
            )

            # umbrales de votacion
            axs[0, 0].axhline(
                limite_si,
                linestyle="--",
                color="#1B5E20",
                linewidth=2,
                label="Umbral SI"
            )

            axs[0, 0].axhline(
                limite_no,
                linestyle="--",
                color="#B71C1C",
                linewidth=2,
                label="Umbral NO"
            )
            axs[0, 0].plot(
                [],
                [],
                color="#1565C0",
                linestyle=":",
                linewidth=2,
                label="Acuerdo alcanzado" )

            # acuerdos alcanzados
            for _, row in self.df_votaciones.iterrows():

                if row["Resultado"] != EN_DEBATE:

                    axs[0, 0].axvline(
                        row["Fin"],
                        color="#1565C0",
                        linestyle=":",
                        linewidth=2,
                        alpha=0.9
                    )

            axs[0, 0].set_title(
                "Evolución de la Postura Promedio y Momentos de Acuerdo",
                fontweight="bold"
            )

            axs[0, 0].set_xlabel("Tiempo")

            axs[0, 0].set_ylabel("Postura ideológica")

            axs[0, 0].set_ylim(0, 1)

            axs[0, 0].legend(loc="upper right")
            # ==========================================================

            # desv. postura
            axs[0, 1].plot(
                tiempo,
                desviacion,
                color="#C9A0FF",
                linewidth=3)

            axs[0, 1].set_title(
                "Dispersión Ideológica de la Asamblea",
                fontweight="bold" )

            axs[0, 1].set_xlabel("Tiempo")
            axs[0, 1].set_ylabel("Desviación Estándar")

            # ============================================================
            # histograma de postura inicial

            axs[1, 0].hist(
                posturas_iniciales,
                bins=15,
                color="#FFD3A5",
                edgecolor="white",
                alpha=0.9  )

            axs[1, 0].axvline(
                np.mean(posturas_iniciales),
                linestyle="--",
                color="gray",
                linewidth=2,
                label=f"Media = {np.mean(posturas_iniciales):.2f}"   )

            axs[1, 0].set_title(
                "Distribución de Posturas Ideológicas Iniciales",
                fontweight="bold"  )

            axs[1, 0].set_xlabel("Postura Ideológica Inicial")
            axs[1, 0].set_ylabel("Frecuencia")

            axs[1, 0].set_xlim(0, 1)

            axs[1, 0].legend(loc="upper right")
            # ===========================================================
            #histograma de postura final

            axs[1, 1].hist(
                posturas_finales,
                bins=15,
                color="#FFD3A5",
                edgecolor="white",
                alpha=0.9
            )
            axs[1, 1].axvline(
                np.mean(posturas_finales),
                linestyle="--",
                color="gray",
                linewidth=2,
                label=f"Media = {np.mean(posturas_finales):.2f}"
            )

            axs[1, 1].set_title(
                "Distribución de Posturas Ideológicas Finales",
                fontweight="bold"
            )
            axs[1, 1].set_xlabel("Postura Ideológica Final")
            axs[1, 1].set_ylabel("Frecuencia")

            axs[1, 1].set_xlim(0, 1)

            axs[1, 1].legend(loc="upper right")

            fig.tight_layout(rect=[0, 0, 1, 0.95])

            plt.show()

            # ========================================================================
            #ventana 2, 2 graficos
            fig2, axs2 = plt.subplots(2, 1, figsize=(15, 8))

            # ============================================================
            # trayectoria temporal

            axs2[0].plot(
                tiempo,
                promedio,
                color="#4D96FF",
                linewidth=3,
                label="Media"
            )

            axs2[0].fill_between(
                tiempo,
                promedio - desviacion,
                promedio + desviacion,
                color="#A9D6FF",
                alpha=0.35,
                label="± 1 Desviación Estándar"
            )


            axs2[0].axhline(
                limite_si,
                linestyle="--",
                color="green",
                linewidth=2,
                label="Umbral SI"
            )

            axs2[0].axhline(
                limite_no,
                linestyle="--",
                color="red",
                linewidth=2,
                label="Umbral NO"
            )

            axs2[0].set_title(
                "Trayectoria Temporal de la Media de la Postura Ideológica",
                fontweight="bold"
            )

            axs2[0].set_xlabel("Tiempo")
            axs2[0].set_ylabel("Postura Ideológica")

            axs2[0].set_ylim(0, 1)

            axs2[0].legend(loc="upper right")
            #-------------Quorum

            apoyo_si = self.df_tiempo["Apoyo SI"]
            apoyo_no = self.df_tiempo["Apoyo NO"]

            # quorum
            axs2[1].plot(
                tiempo,
                quorum,
                color="#1B4332",
                linewidth=3,
                linestyle="--",
                label="Quorum"
            )

            # apoyo SI
            axs2[1].plot(
                tiempo,
                apoyo_si,
                color="#2E7D32",
                linewidth=3,
                label="Apoyo SI"
            )

            # apoyo NO
            axs2[1].plot(
                tiempo,
                apoyo_no,
                color="#C62828",
                linewidth=3,
                label="Apoyo NO"
            )

            axs2[1].set_title(
                "Dinamica de Quorum y Apoyo",
                fontweight="bold"
            )

            axs2[1].set_xlabel("Tiempo")

            axs2[1].set_ylabel("Estudiantes")

            axs2[1].legend(loc="upper right")

            fig2.tight_layout(rect=[0, 0, 1, 0.95])
            plt.show()

        return {
            "df_intervenciones": self.df_intervenciones,
            "df_votaciones": self.df_votaciones,
            "df_estudiantes": df_estudiantes,
            "df_tiempo": self.df_tiempo
        }


def n_run(n=50,confianza=0.95,df=False,graficos=True,resumen=True):
    """
    Ejecuta multiples simulaciones independientes del modelo.

    Variables analizadas:
        - numero de acuerdos alcanzados
        - numero de intervenciones
        - total de estudiantes participantes
        - tiempo hasta el primer acuerdo
        - desviacion inicial de posturas
        - desviacion final de posturas
        - tiempo promedio de salida

    Adicionalmente se estima la probabilidad de alcanzar
    al menos un acuerdo mediante:

        p = exitos / n

    donde:
        exitos = simulaciones con al menos un acuerdo

    Tambien se estima la proporcion promedio de estudiantes
    que desertaron durante la asamblea.

    Para ambas proporciones se calcula un intervalo de confianza
    utilizando una aproximacion normal:

        error = z * sqrt((p * (1 - p)) / n)

        limite_inferior = p - error
        limite_superior = p + error

    Parametros
        n : int, default=50
            Numero de simulaciones independientes.

        confianza : float, default=0.95
            Nivel de confianza estadistica.

        df : bool, default=False
            Indica si se imprime el dataframe agregado.

        graficos : bool, default=True
            Indica si se generan histogramas.

        resumen : bool, default=True
            Indica si se imprime el resumen estadistico.

    Return
        pandas.DataFrame
            Dataframe con resultados agregados de
            todas las ejecuciones.
    """
    acuerdos = []
    intervenciones = []
    total_estudiantes = []
    tiempo_primer_acuerdo = []
    desv_inicial=[]
    desv_final=[]
    tiempo_promedio_salida=[]
    tasa_abandono=[]
    

    for _ in range(n):

        modelo = Asamblea()

        resultados = modelo.run_model(
            df=False,
            graficos=False,
            resumen=False)
        
        df_est = resultados["df_estudiantes"]
        df_vot = resultados["df_votaciones"]

        desv_inicial.append(df_est["Postura Inicial"].std()) 
        desv_final.append(df_est["Postura Final"].std())
        
        acuerdos_df = modelo.df_votaciones[modelo.df_votaciones["Resultado"] != EN_DEBATE]
        if len(acuerdos_df) > 0:
            tiempo_primer_acuerdo.append(acuerdos_df.iloc[0]["Fin"])
        else:
            tiempo_primer_acuerdo.append(np.nan)


        salidas = df_est["Tiempo Salida"].dropna()
        if len(salidas) > 0:
            tiempo_promedio_salida.append(salidas.mean())
        else:
            tiempo_promedio_salida.append(np.nan)

        abandonaron = (~df_est["Activo"]).sum()
        tasa_abandono.append(abandonaron / len(df_est))

        acuerdos.append(modelo.id_propuesta - 1)

        intervenciones.append(modelo.numero_intervenciones)

        total_estudiantes.append(len(modelo.estudiantes))
        
    p = sum(a >= 1 for a in acuerdos) / n

    if confianza == 0.90:
        z = 1.645

    elif confianza == 0.95:
        z = 1.96

    elif confianza == 0.99:
        z = 2.576

    else:
        raise ValueError("Usa confianza = 0.90, 0.95 o 0.99")

    error = z * np.sqrt((p * (1 - p)) / n)
    li = max(0, p - error)
    ls = min(1, p + error)

    p_desercion = np.mean(tasa_abandono)

    error_desercion = z * np.sqrt(
        (p_desercion * (1 - p_desercion)) / n)

    li_desercion = max(
        0,
        p_desercion - error_desercion)

    ls_desercion = min(
        1,
        p_desercion + error_desercion)

    if resumen:

        print("\n" + "=" * 70)
        print(f"RESULTADOS DE {n} EJECUCIONES")
        print("=" * 70)

        print(f"Escenario:                          {ESCENARIO.upper()}")
        print(f"Promedio de acuerdos:               {np.mean(acuerdos):.2f}")
        print(f"Promedio de intervenciones:         {np.mean(intervenciones):.2f}")
        print(f"Promedio de estudiantes:            {np.mean(total_estudiantes):.2f}")

        print(f"Tiempo promedio para lograr \n"
              f"el primer acuerdo:                  {np.nanmean(tiempo_primer_acuerdo):.2f}")

        print(f"Tiempo promedio de salida \n"
              f"de los estudiantes:                 {np.nanmean(tiempo_promedio_salida):.2f}")

        print(f"Media de la dispersión ideológica\n"
              f"(desv. estándar) inicial:           {np.mean(desv_inicial):.4f}")

        print(f"Media de la dispersión ideológica\n"
              f"(desv. estándar) final:             {np.mean(desv_final):.4f}")
 
        print("-" * 70)

        print(f"Con un intervalo de confianza del {int(confianza * 100)}%, la probabilidad\n"
            f"de alcanzar al menos un acuerdo durante la asamblea se encuentra \n"
            f"entre {li * 100:.2f}% y {ls * 100:.2f}%.\n" )

        print(f"Con un intervalo de confianza del {int(confianza * 100)}%, el porcentaje \n"
            f"de estudiantes que abandonaron la asamblea antes de su finalización se \n"
            f"encuentra entre {li_desercion * 100:.2f}% y {ls_desercion * 100:.2f}%." )

        print("=" * 70)

    df_resultados = pd.DataFrame({
        "Acuerdos": acuerdos,
        "Intervenciones": intervenciones,
        "Total Estudiantes": total_estudiantes})

    if df:
        print("\nDATAFRAME RESULTADOS\n")
        print(df_resultados)

    if graficos:

        plt.rcParams.update({
            "axes.facecolor": "#FAFAFA",
            "figure.facecolor": "white",
            "axes.grid": True,
            "grid.alpha": 0.25,
            "grid.linestyle": "--",
            "font.size": 10
        })

        # ventana 1

        fig1, axs1 = plt.subplots(2, 2, figsize=(14, 8))

        fig1.suptitle(
            f"({n} ejecuciones) - Escenario {ESCENARIO.upper()}",
            fontsize=18,
            fontweight="bold")

        # Acuerdos
        axs1[0,0].hist(acuerdos, bins=10, color="#89C2F7",
                    edgecolor="white", alpha=0.9)
        axs1[0,0].axvline(np.mean(acuerdos), linestyle="--",
                        color="gray", linewidth=2,
                        label=f"Media = {np.mean(acuerdos):.2f}")
        axs1[0,0].set_title("Distribución del Número de Acuerdos", fontweight="bold")
        axs1[0,0].set_xlabel("Número Acuerdos")
        axs1[0,0].set_ylabel("Frecuencia")
        axs1[0,0].legend(loc="upper right")

        # Intervenciones
        axs1[0,1].hist(intervenciones, bins=10, color="#C9A0FF",
                    edgecolor="white", alpha=0.9)
        axs1[0,1].axvline(np.mean(intervenciones), linestyle="--",
                        color="gray", linewidth=2,
                        label=f"Media = {np.mean(intervenciones):.2f}")
        axs1[0,1].set_title("Distribución del Número de Intervenciones", fontweight="bold")
        axs1[0,1].set_xlabel("Número Intervenciones")
        axs1[0,1].set_ylabel("Frecuencia")
        axs1[0,1].legend(loc="upper right")

        # Estudiantes
        axs1[1,0].hist(total_estudiantes, bins=10, color="#FFD3A5",
                    edgecolor="white", alpha=0.9)
        axs1[1,0].axvline(np.mean(total_estudiantes), linestyle="--",
                        color="gray", linewidth=2,
                        label=f"Media = {np.mean(total_estudiantes):.2f}")
        axs1[1,0].set_title("Distribución del Número de Participantes", fontweight="bold")
        axs1[1,0].set_xlabel("Total Estudiantes")
        axs1[1,0].set_ylabel("Frecuencia")
        axs1[1,0].legend(loc="upper right")

        # Tiempo primer acuerdo
        axs1[1,1].hist(tiempo_primer_acuerdo, bins=10, color="#118AB2",
                    edgecolor="white", alpha=0.9)
        axs1[1,1].axvline(np.nanmean(tiempo_primer_acuerdo), linestyle="--",
                        color="gray", linewidth=2,
                        label=f"Media = {np.nanmean(tiempo_primer_acuerdo):.2f}")
        axs1[1,1].set_title("Tiempo hasta el Primer Acuerdo",
                            fontweight="bold")
        axs1[1,1].set_xlabel("Tiempo")
        axs1[1,1].set_ylabel("Frecuencia")
        axs1[1,1].legend(loc="upper right")

        plt.tight_layout()
        plt.show()

        # Ventana 2
        fig2, axs2 = plt.subplots(2, 2, figsize=(14, 8))

        fig2.suptitle(
            f"Indicadores Sociales - Escenario {ESCENARIO.upper()}",
            fontsize=18,
            fontweight="bold"
        )

        # Desviación inicial
        axs2[0,0].hist(desv_inicial, bins=10, color="#FFD166",
                    edgecolor="white", alpha=0.9)
        axs2[0,0].axvline(np.mean(desv_inicial), linestyle="--",
                        color="gray", linewidth=2,
                        label=f"Media = {np.mean(desv_inicial):.3f}")
        axs2[0,0].set_title("Dispersión Ideológica Inicial",
                            fontweight="bold")
        axs2[0,0].set_xlabel("Desviación Estándar")
        axs2[0,0].set_ylabel("Frecuencia")
        axs2[0,0].legend(loc="upper right")

        # Desviación final
        axs2[0,1].hist(desv_final, bins=10, color="#EF476F",
                    edgecolor="white", alpha=0.9)
        axs2[0,1].axvline(np.mean(desv_final), linestyle="--",
                        color="gray", linewidth=2,
                        label=f"Media = {np.mean(desv_final):.3f}")
        axs2[0,1].set_title("Dispersión Ideológica Final",
                            fontweight="bold")
        axs2[0,1].set_xlabel("Desviación Estándar")
        axs2[0,1].set_ylabel("Frecuencia")
        axs2[0,1].legend(loc="upper right")

        # Tasa abandono
        axs2[1,0].hist(tasa_abandono, bins=10, color="#06D6A0",
                    edgecolor="white", alpha=0.9)
        axs2[1,0].axvline(np.mean(tasa_abandono), linestyle="--",
                        color="gray", linewidth=2,
                        label=f"Media = {np.mean(tasa_abandono):.3f}")
        axs2[1,0].set_title("Proporción de Estudiantes que Desertaron",
                            fontweight="bold")
        axs2[1,0].set_xlabel("Proporción")
        axs2[1,0].set_ylabel("Frecuencia")
        axs2[1,0].legend(loc="upper right")

        # Tiempo promedio salida
        axs2[1,1].hist(tiempo_promedio_salida, bins=10, color="#A8DADC",
                    edgecolor="white", alpha=0.9)
        axs2[1,1].axvline(np.nanmean(tiempo_promedio_salida), linestyle="--",
                        color="gray", linewidth=2,
                        label=f"Media = {np.nanmean(tiempo_promedio_salida):.2f}")
        axs2[1,1].set_title("Tiempo Promedio de Permanencia antes de la Salida",
                            fontweight="bold")
        axs2[1,1].set_xlabel("Tiempo")
        axs2[1,1].set_ylabel("Frecuencia")
        axs2[1,1].legend(loc="upper right")

        plt.tight_layout()
        plt.show()

    return df_resultados
# =============================================================================================
# EJECUCION
modelo = Asamblea()
modelo.run_model()
n_run(6)
# ==========================================================================================