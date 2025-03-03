# SLMD


Para publicar seria de la siguiente manera: sensor/ID/"Metricas"

El ID esta hecho de la siguiente manera:
ID= str(uuid.uuid4())
Ejemplo:28c40769-1919-420a-8eb1-7449d56a0a7f 
Siendo las metricas estas:
"acelerometro"
"giroscopio"
"magnetometro"
"barometro"
"gps"
Y la manera de publicarlo seria en formato json de la manera siguiente:
acelerometro: {
  "x": -8.257,
  "y": -8.256,
  "z": -8.256
}
giroscopio: {
  "x": -1032.024,
  "y": -1032.015,
  "z": -1032.009
}
magnetometro: {
  "x": -2528.401,
  "y": -2528.39,
  "z": -2528.373
}
barometro: {
  "presion": 502.005
}
gps: {
  "hora": "210401",
  "latitud": 40.012421,
  "longitud": -2.987579
}
