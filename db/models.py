from datetime import datetime

from sqlalchemy import Integer, BigInteger, String, DateTime, Float, JSON, ForeignKey, \
    Boolean, func
from sqlalchemy.orm import relationship, Mapped, mapped_column

from db.db_config import Base
from logic.base import BaseModel


# Модель для пользователей
class User(Base, BaseModel):
    __tablename__ = 'users'

    id: Mapped[BigInteger] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str] = mapped_column(String(255), unique=True, nullable=True)
    date_reg: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(), server_default=func.now())
    full_name: Mapped[str] = mapped_column(String(255))

    # Связь с комнатами через таблицу user_room
    rooms: Mapped[list["Box"]] = relationship(
        "Box",
        secondary="user_room",
        back_populates="participants",
        lazy="immediate",
        primaryjoin="User.id == UserRoom.user_id",
        secondaryjoin="Box.id == UserRoom.box_id"
    )
    # Связь с подарками
    gifts: Mapped[list["Gift"]] = relationship("Gift", back_populates="user", lazy="immediate")


# Модель для комнат (Коробок)
class Box(Base, BaseModel):
    __tablename__ = 'boxes'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    join_code: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    final_reg_date: Mapped[datetime] = mapped_column(DateTime)
    max_gift_price: Mapped[Float] = mapped_column(Float)
    gift_date: Mapped[datetime] = mapped_column(DateTime)

    # Связь с пользователем-админом
    admin_id: Mapped[BigInteger] = mapped_column(BigInteger, ForeignKey('users.id'))
    admin: Mapped["User"] = relationship("User", backref="admin_of_boxes", lazy="immediate")

    # Связь с участниками через таблицу user_room
    participants: Mapped[list[User]] = relationship(
        "User",
        secondary="user_room",
        back_populates="rooms",
        lazy="immediate",
        primaryjoin="Box.id == UserRoom.box_id",
        secondaryjoin="User.id == UserRoom.user_id"
    )

    # Связь с подарками
    gifts: Mapped[list["Gift"]] = relationship("Gift", back_populates="box", lazy="immediate")


# Таблица связи между пользователями и комнатами (многие ко многим)
class UserRoom(Base, BaseModel):
    __tablename__ = 'user_room'

    user_id: Mapped[BigInteger] = mapped_column(BigInteger, ForeignKey('users.id'), primary_key=True)
    box_id: Mapped[int] = mapped_column(Integer, ForeignKey('boxes.id'), primary_key=True)
    profile: Mapped[dict] = mapped_column(JSON)
    user_gift_to_id: Mapped[BigInteger] = mapped_column(BigInteger, ForeignKey('users.id'), nullable=True)

    # Отношение для удобства
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id], lazy="immediate")
    receiver: Mapped["User"] = relationship("User", foreign_keys=[user_gift_to_id], lazy="immediate")

# Модель для подарков
class Gift(Base, BaseModel):
    __tablename__ = 'gifts'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    box_id: Mapped[int] = mapped_column(Integer, ForeignKey('boxes.id'), nullable=False)
    user_id: Mapped[BigInteger] = mapped_column(BigInteger, ForeignKey('users.id'), nullable=False)
    gift_url: Mapped[str] = mapped_column(String(255), nullable=False)
    price: Mapped[Float] = mapped_column(Float, nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=True)
    is_exact: Mapped[bool] = mapped_column(Boolean, nullable=False)

    # Связь с комнатой и пользователем
    box: Mapped["Box"] = relationship("Box", back_populates="gifts", lazy="immediate")
    user: Mapped["User"] = relationship("User", back_populates="gifts", lazy="immediate")