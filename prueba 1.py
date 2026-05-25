import random
import numpy as np
import pandas as pd

# Parametros
AFORO_MAXIMO = 100
TIEMPO_MAXIMO = 240
INTERVENCIONES_POR_VOTACION = 10
TIEMPO_VOTACION = 1
MIN_ESTUDIANTES = 5 
TASA_LLEGADAS = 1 / 2
APERTURA_DIALOGO = 0.35
UMBRAL_IDEOLOGICO = 0.5
TASA_SALIDA = 1/180
LIMITES_VOTACION = (0.4, 0.6)
ALCANCE_INTERVENCION= 0.65 
ESTANCAMIENTO_INICIAL = 1
AUMENTO_ESTANCAMIENTO = 0.2
ESTUDIANTES_INICIALES = 20
FACTOR_POLARIZACION = 2


#Estados de la propuesta
EN_DEBATE = "Propuesta en debate"
APROBADA = "Propuesta aprobada"
NEGADA = "Propuesta negada"


class Estudiante:

    def __init__(self, id_estudiante, tiempo_llegada):
        self.id = id_estudiante
        self.postura = random.uniform(0, 1)
        self.postura_inicial = self.postura
        self.persuasion = random.uniform(0, 1)

        self.tolerancia = np.random.exponential(1/TASA_SALIDA)

        self.tolerancia_inicial = (self.tolerancia)
        self.tiempo_intervencion = 0
        self.duracion_intervencion = random.randint(2,7)
        self.tiempo_llegada = tiempo_llegada
        self.activo = True
        self.tiempo_salida = np.nan
    def intervenir(self, estudiantes_activos):
        #Estudiantes que estan escuchando
        influenciados = [e for e in estudiantes_activos if e.id != self.id and random.random()<ALCANCE_INTERVENCION] 
        if len(influenciados) == 0:
            return [], 0, 0, 0
        
        promedio_inicial = np.mean([e.postura for e in influenciados])
        desv_polarizacion = np.std([e.postura for e in influenciados])

        for i in influenciados:
            diferencia = abs(self.postura - i.postura)

            polarizacion = (1+ FACTOR_POLARIZACION* diferencia* desv_polarizacion)

            cambio = (self.persuasion
                *(self.postura- i.postura)
                *np.exp(-diferencia/ APERTURA_DIALOGO))

            if diferencia <= UMBRAL_IDEOLOGICO:
                i.postura += cambio
            else:
                i.postura -= cambio

            i.postura = max(0,min(1, i.postura))

        promedio_final = np.mean([e.postura for e in influenciados])

        return (promedio_inicial,promedio_final,len(influenciados),desv_polarizacion)
# Variables
estudiantes = []
tiempo_actual = 0
numero_intervenciones = 0
contador_ids = 1 
id_propuesta = 1
inicio_propuesta = 0
estancamiento = ESTANCAMIENTO_INICIAL

proxima_llegada = np.random.exponential(scale=1 / TASA_LLEGADAS)

df_votaciones = pd.DataFrame(columns=[
    "ID Propuesta","Inicio de Votación","Fin de Votación",
    "Número Estudiantes","Quorum","Votos SI","Votos NO",
    "Abstenciones","Resultado","Tiempo de Aprobación",
    "Votacion Final"
])

df_intervenciones = pd.DataFrame(columns=[
    "ID Estudiante","Duración",
    "Inicio","Fin","Estudiantes Presentes",
    "Estudiantes Influenciados","Postura Promedio Inicial"
])


def activos():
    return [e for e in estudiantes if e.activo]


def calcular_quorum():
    presentes = len(activos())
    return (presentes // 2) + 1


def votar():
    global id_propuesta
    global inicio_propuesta
    global tiempo_actual
    global estancamiento

    votos_si = 0
    votos_no = 0
    abstenciones = 0

    presentes = len(activos())
    quorum = calcular_quorum()
    limite_no, limite_si = LIMITES_VOTACION
    inicio_votacion = round(tiempo_actual,2)
    for e in activos():

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

    tiempo_aprobacion = np.nan

    tiempo_actual += TIEMPO_VOTACION
    for e in activos():
        e.tolerancia -= TIEMPO_VOTACION*estancamiento
        if e.tolerancia <= 0:
            e.activo = False
            e.tiempo_salida = round(tiempo_actual,2)

    if resultado != EN_DEBATE:
        tiempo_aprobacion = round(tiempo_actual - inicio_propuesta,2)
        estancamiento = ESTANCAMIENTO_INICIAL
    else:
        estancamiento *= (1 + AUMENTO_ESTANCAMIENTO)

    df_votaciones.loc[len(df_votaciones)] = {
        "ID Propuesta": id_propuesta,
        "Inicio de Votación":inicio_votacion,
        "Fin de Votación": round(tiempo_actual,2),
        "Número Estudiantes":presentes,
        "Quorum":quorum,
        "Votos SI":votos_si,
        "Votos NO":votos_no,
        "Abstenciones":abstenciones,
        "Resultado":resultado,
        "Tiempo de Aprobación":tiempo_aprobacion}
    
    #Pasamos a la siguiente propuesta
    if resultado != EN_DEBATE:
        id_propuesta += 1
        inicio_propuesta = tiempo_actual

for i in range(ESTUDIANTES_INICIALES):
    nuevo = Estudiante(contador_ids,0)
    estudiantes.append(nuevo)
    contador_ids += 1

# SIMULACION
while tiempo_actual < TIEMPO_MAXIMO:

    while (tiempo_actual >= proxima_llegada and len(activos()) < AFORO_MAXIMO):
        nuevo = Estudiante(contador_ids,proxima_llegada)

        estudiantes.append(nuevo)
        contador_ids += 1
        proxima_llegada += np.random.exponential(scale=1 / TASA_LLEGADAS)

    estudiantes_presentes = activos()

    if (tiempo_actual >= TIEMPO_MAXIMO and len(estudiantes_presentes) < MIN_ESTUDIANTES):
        break

    if len(estudiantes_presentes) < MIN_ESTUDIANTES:
        tiempo_actual = min(proxima_llegada,TIEMPO_MAXIMO)
        continue

    orador = random.choice(estudiantes_presentes)

    inicio_intervencion = tiempo_actual

    (promedio_inicial,promedio_final,influenciados,desv_polarizacion) = orador.intervenir(estudiantes_presentes)

    tiempo_actual += (orador.duracion_intervencion)
    fin_intervencion = tiempo_actual
    numero_intervenciones += 1
    orador.tiempo_intervencion += (orador.duracion_intervencion)

    df_intervenciones.loc[len(df_intervenciones)] = {
        "ID Estudiante":orador.id,
        "Duración":orador.duracion_intervencion,
        "Inicio": round(inicio_intervencion,2),
        "Fin":round(fin_intervencion,2),
        "Estudiantes Presentes":len(estudiantes_presentes),
        "Estudiantes Influenciados":influenciados,
        "Postura Promedio Inicial":promedio_inicial,
        "Postura Promedio Final":promedio_final}

    for e in estudiantes_presentes:
        diferencia = abs(orador.postura - e.postura)
        polarizacion = (1+ FACTOR_POLARIZACION * diferencia* desv_polarizacion)

        desgaste = (orador.duracion_intervencion* estancamiento * polarizacion)

        e.tolerancia -= desgaste

        if e.tolerancia <= 0:
            e.activo = False
            e.tiempo_salida = round(tiempo_actual,2)

    if (numero_intervenciones%INTERVENCIONES_POR_VOTACION== 0 and len(activos()) >= MIN_ESTUDIANTES):
        votar()

if (len(activos())>= MIN_ESTUDIANTES and numero_intervenciones%INTERVENCIONES_POR_VOTACION != 0):
    votar()

df_estudiantes = pd.DataFrame([{
    "ID Estudiante":e.id,
    "Postura Inicial":round(e.postura_inicial,4),
    "Postura Final":round(e.postura,4),
    "Persuasión":round(e.persuasion,4),
    "Tolerancia Inicial":round(e.tolerancia_inicial,2),
    "Tolerancia Restante":round(e.tolerancia,2),
    "Tiempo de Intervencion":round(e.tiempo_intervencion,2),
    "Tiempo de Llegada":round(e.tiempo_llegada,2),
    "Tiempo de Salida":e.tiempo_salida,
    "Activo":e.activo
    } for e in estudiantes])

#Resultados
print("\nVOTACIONES\n")
print(df_votaciones)

print("\nINTERVENCIONES\n")
print(df_intervenciones)

print("\nESTUDIANTES\n")
print(df_estudiantes)

print(" Tiempo Final:",round(tiempo_actual,2),"\n",
    "Intervenciones Totales:",numero_intervenciones,"\n",
    "Acuerdos logrados:",id_propuesta - 1,"\n",
    "Estudiantes Presentes:",len(activos()),"\n",
    "Total Estudiantes:",len(estudiantes))