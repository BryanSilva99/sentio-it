from __future__ import annotations


def classify_pm25(pm25: float) -> dict[str, str | int | float]:
    """Clasificacion simplificada basada en PM2.5 para el MVP."""
    if pm25 <= 12:
        return {"level": "Bueno", "color": "green", "score": 100}
    if pm25 <= 35.4:
        return {"level": "Moderado", "color": "yellow", "score": 70}
    if pm25 <= 55.4:
        return {"level": "Malo para sensibles", "color": "orange", "score": 45}
    if pm25 <= 150.4:
        return {"level": "Malo", "color": "red", "score": 20}
    return {"level": "Peligroso", "color": "purple", "score": 5}


def recommendation(pm25: float) -> str:
    if pm25 <= 12:
        return "Aire limpio. Buen momento para actividades al aire libre."
    if pm25 <= 35.4:
        return "Calidad aceptable. Personas sensibles deben monitorear sintomas."
    if pm25 <= 55.4:
        return "Reducir ejercicio intenso al aire libre si eres sensible."
    if pm25 <= 150.4:
        return "Evitar exposicion prolongada al aire libre."
    return "Permanecer en interiores y usar proteccion si debes salir."

