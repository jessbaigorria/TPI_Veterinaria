"""Persistencia del State (string + @orm.reconstructor) y del Observer al recargar."""
from app.domain.estados.estado_muestra import EnTransito
from app.domain.estados import estado_remito
from app.domain.muestra import MuestraBiologica
from app.domain.observadores.observadores_muestra import ActualizadorEstadoOrden, RegistroHistorial
from app.domain.transporte import RemitoBiologico
from app import db as db_mod


def test_estado_se_persiste_como_string_y_se_rehidrata(engine, base):
    m = base.muestra()
    r = base.remito_en_transito([m])
    with engine.connect() as c:
        assert c.exec_driver_sql("select estado from muestra_biologica where id=?", (m.id,)).scalar() == "EnTransito"
        assert c.exec_driver_sql("select estado from remito_biologico where id=?", (r.id,)).scalar() == "EnTransito"
    otra = db_mod.crear_fabrica_sesiones(engine)()
    m2 = otra.get(MuestraBiologica, m.id)
    assert isinstance(m2.estado, EnTransito)
    assert isinstance(otra.get(RemitoBiologico, r.id).estado, estado_remito.EnTransito)
    # al cargar desde la base también se adjuntan los observadores (un único lugar)
    assert {type(o) for o in m2._observadores()} == {RegistroHistorial, ActualizadorEstadoOrden}
    otra.close()


def test_muestra_recargada_sigue_registrando_historial(engine, base):
    m = base.muestra()
    r = base.remito_en_transito([m])
    otra = db_mod.crear_fabrica_sesiones(engine)()
    from app.services.recepcion import RecepcionService
    RecepcionService(otra).recibir(r.id, base.lab.id, True, 4, "Otra Persona")
    m2 = otra.get(MuestraBiologica, m.id)
    assert m2.historial()[-1].usuario == "Otra Persona"
    assert len(m2.historial()) == 4
    otra.close()


def test_rollback_deja_el_estado_consistente(sesion, base):
    import pytest
    from app.domain.excepciones import TransicionInvalidaError
    from app.services.envios import EnviosService
    m = base.muestra()
    r = base.remito_en_transito([m])
    with pytest.raises(TransicionInvalidaError):
        EnviosService(sesion).confirmar_retiro(r.id)  # ya está en tránsito
    assert r.estado_codigo == "EnTransito"
    assert isinstance(sesion.get(MuestraBiologica, m.id).estado, EnTransito)


def test_numeracion_automatica(base):
    m = base.muestra()
    assert m.codigo.startswith("M-") and len(m.codigo) == 8
    assert m.orden.numero.startswith("ORD-")
    assert base.firulais.historia_clinica.numero.startswith("HC-")


def test_migracion_de_nombres_viejos_de_estado_de_remito(engine, base):
    # Bases creadas antes del cambio guardaban «RemitoEnTransito»: init_db las actualiza al arrancar.
    r = base.remito_en_transito([base.muestra()])
    base.s.commit()
    with engine.begin() as c:
        c.exec_driver_sql("update remito_biologico set estado = 'RemitoEnTransito' where id = ?", (r.id,))
    db_mod.init_db(engine)
    with engine.connect() as c:
        assert c.exec_driver_sql("select estado from remito_biologico where id=?", (r.id,)).scalar() == "EnTransito"
    otra = db_mod.crear_fabrica_sesiones(engine)()
    assert isinstance(otra.get(RemitoBiologico, r.id).estado, estado_remito.EnTransito)
    otra.close()
