"""Controlador de créditos: solicitar crédito (ME/CO)."""
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.engine import Connection

from app.repositories import repo_creditos


def solicitar(
    conn: Connection,
    pkcliente: int,
    montosolicitud: Decimal,
    plazo: int,
    codtipocredito: str,
    codactividadeconomica: str,
    montoingresoneto: Decimal,
) -> dict:
    if codtipocredito not in repo_creditos.MAPA_TIPO_CREDITO:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tipo de crédito fuera de alcance (solo ME o CO)",
        )
    try:
        res = repo_creditos.crear_solicitud(
            conn,
            pkcliente=pkcliente,
            montosolicitud=montosolicitud,
            plazo=plazo,
            codtipocredito=codtipocredito,
            codactividadeconomica=codactividadeconomica,
            montoingresoneto=montoingresoneto,
        )
    except ValueError as e:
        if "Semáforo ROJO" in str(e):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return {
        "mensaje": "Solicitud registrada (En Evaluación)",
        "estado": "En Evaluación",
        "montosolicitud": montosolicitud,
        "plazo": plazo,
        **res,
    }


def simular_credito(
    monto: Decimal,
    tea: Decimal,
    plazo: int,
    tipo_desgravamen: str = "estandar",
    seguro_vida_tranki: bool = False,
    es_convenio: bool = False,
) -> dict:
    """
    Simula la cuota mensual de un crédito bajo el método francés,
    aplicando seguro de desgravamen, comisiones e ITF.
    """
    # Tasa efectiva mensual
    tea_float = float(tea) / 100
    im = (1 + tea_float) ** (30 / 360) - 1
    im_dec = Decimal(str(im))

    # Tasa de desgravamen
    id_tasa = Decimal("0")
    if tipo_desgravamen == "estandar":
        id_tasa = Decimal("0.0012")  # 0.12% mensual (Banco de la Nación)
    elif tipo_desgravamen == "rescate":
        id_tasa = Decimal("0.00133")   # 0.133% mensual con retorno (Banco de la Nación)

    monto_financiar = Decimal(monto)
    
    # Seguro Vida Tranki
    if seguro_vida_tranki:
        t_vt = Decimal("0.0000148")  # 0.00148%
        dias_totales = plazo * 30
        prima_vt = monto_financiar * Decimal(dias_totales) * t_vt
        monto_financiar += prima_vt

    # Comisión por planilla
    cp = Decimal("5.00") if es_convenio else Decimal("0.00")

    # Seguro Desgravamen en base al saldo inicial para la primera cuota
    sd = monto_financiar * id_tasa

    # Cuota pura total (Interés + Amortización + Desgravamen) usando la tasa combinada
    im_total = im + float(id_tasa)
    if im_total > 0 and plazo > 0:
        factor = (1 + im_total) ** -plazo
        cuota_total_pura_float = (float(monto_financiar) * im_total) / (1 - factor)
    else:
        cuota_total_pura_float = float(monto_financiar) / plazo if plazo > 0 else 0
        
    cuota_total_pura = Decimal(str(cuota_total_pura_float))
    
    # Cuota pura sin desgravamen (para desglose en la interfaz)
    cuota_pura = cuota_total_pura - sd

    # Subtotal para calcular ITF
    subtotal = cuota_total_pura + cp
    itf = subtotal * Decimal("0.00005")

    cuota_total = subtotal + itf

    return {
        "monto_financiar": round(monto_financiar, 2),
        "cuota_pura": round(cuota_pura, 2),
        "seguro_desgravamen": round(sd, 2),
        "comision_planilla": round(cp, 2),
        "itf": round(itf, 2),
        "cuota_total": round(cuota_total, 2),
    }
