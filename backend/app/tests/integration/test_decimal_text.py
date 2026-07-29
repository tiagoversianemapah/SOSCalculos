from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import StatementError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from app.models.tipos import DecimalText


class _Base(DeclarativeBase):
    pass


class _Amostra(_Base):
    __tablename__ = "amostra_decimal"

    id: Mapped[int] = mapped_column(primary_key=True)
    valor: Mapped[Decimal | None] = mapped_column(DecimalText(), nullable=True)


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    _Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def test_round_trip_preserva_precisao_total(session):
    valor = Decimal("1234.567890123456789012345678")
    session.add(_Amostra(id=1, valor=valor))
    session.commit()
    session.expunge_all()

    lido = session.get(_Amostra, 1)
    assert lido.valor == valor
    assert str(lido.valor) == str(valor)


def test_round_trip_preserva_zeros_a_direita(session):
    valor = Decimal("1234.5600")
    session.add(_Amostra(id=1, valor=valor))
    session.commit()
    session.expunge_all()

    lido = session.get(_Amostra, 1)
    assert str(lido.valor) == "1234.5600"


def test_armazena_como_text_no_sqlite(session):
    session.add(_Amostra(id=1, valor=Decimal("42.00")))
    session.commit()

    bruto = session.connection().exec_driver_sql(
        "SELECT valor FROM amostra_decimal WHERE id = 1"
    ).scalar_one()
    assert isinstance(bruto, str)
    assert bruto == "42.00"


def test_rejeita_float_na_gravacao(session):
    session.add(_Amostra(id=1, valor=1234.56))  # type: ignore[arg-type]
    with pytest.raises(StatementError) as exc_info:
        session.commit()
    assert isinstance(exc_info.value.orig, TypeError)


def test_aceita_none(session):
    session.add(_Amostra(id=1, valor=None))
    session.commit()
    session.expunge_all()

    assert session.get(_Amostra, 1).valor is None


def test_aceita_string_numerica_e_converte_para_decimal(session):
    session.add(_Amostra(id=1, valor=Decimal("10")))
    session.commit()
    session.expunge_all()

    assert session.get(_Amostra, 1).valor == Decimal("10")
