from __future__ import annotations

from typing import Any

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON


class Base(DeclarativeBase):
    pass


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    address: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False)

    snapshots: Mapped[list[SiteSnapshot]] = relationship(back_populates="project")
    schemes: Mapped[list[SchemeOption]] = relationship(back_populates="project")
    documents: Mapped[list[DocumentSet]] = relationship(back_populates="project")


class SiteSnapshot(Base):
    __tablename__ = "site_snapshots"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    captured_at: Mapped[str] = mapped_column(String, nullable=False)
    zone_code: Mapped[str | None] = mapped_column(String, nullable=True)
    zone_name: Mapped[str | None] = mapped_column(String, nullable=True)
    area_m2: Mapped[float | None] = mapped_column(Float, nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    rules_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    project: Mapped[Project] = relationship(back_populates="snapshots")


class SchemeOption(Base):
    __tablename__ = "scheme_options"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    option_key: Mapped[str] = mapped_column(String, nullable=False)
    typology: Mapped[str | None] = mapped_column(String, nullable=True)
    dwellings: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gfa_m2: Mapped[float | None] = mapped_column(Float, nullable=True)
    verdict: Mapped[str | None] = mapped_column(String, nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    project: Mapped[Project] = relationship(back_populates="schemes")
    estimates: Mapped[list[CostEstimate]] = relationship(back_populates="scheme")


class CostEstimate(Base):
    __tablename__ = "cost_estimates"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    scheme_option_id: Mapped[str] = mapped_column(ForeignKey("scheme_options.id"), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    pricebook_version: Mapped[str | None] = mapped_column(String, nullable=True)
    fee_book_version: Mapped[str | None] = mapped_column(String, nullable=True)
    confirmed_total: Mapped[float | None] = mapped_column(Float, nullable=True)
    missing_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    scheme: Mapped[SchemeOption] = relationship(back_populates="estimates")


class DocumentSet(Base):
    __tablename__ = "document_sets"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    kind: Mapped[str | None] = mapped_column(String, nullable=True)
    filename: Mapped[str | None] = mapped_column(String, nullable=True)
    stored_path: Mapped[str | None] = mapped_column(String, nullable=True)
    captured_at: Mapped[str] = mapped_column(String, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    project: Mapped[Project] = relationship(back_populates="documents")


class PriceBookVersion(Base):
    __tablename__ = "pricebook_versions"

    version: Mapped[str] = mapped_column(String, primary_key=True)
    as_of: Mapped[str | None] = mapped_column(String, nullable=True)
    source_name: Mapped[str | None] = mapped_column(String, nullable=True)
    item_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
