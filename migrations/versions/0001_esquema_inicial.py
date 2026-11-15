"""Esquema inicial (equivalente a la base SQLite v1.6).

Si la base ya tiene las tablas (el atf_assistant.db histórico), las adopta:
crea solo las que faltan y agrega las columnas de revisión si no están.

Revision ID: 0001
"""
import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def _tables():
    """(nombre, columnas, restricciones extra) en orden de dependencias."""
    pk = lambda: sa.Column("id", sa.Integer, primary_key=True, autoincrement=True)  # noqa: E731
    now = sa.text("CURRENT_TIMESTAMP")
    return [
        ("brands", [pk(), sa.Column("name", sa.Text, nullable=False, unique=True),
                    sa.Column("country", sa.Text)]),
        ("models", [pk(),
                    sa.Column("brand_id", sa.Integer, sa.ForeignKey("brands.id", ondelete="CASCADE"), nullable=False),
                    sa.Column("name", sa.Text, nullable=False),
                    sa.UniqueConstraint("brand_id", "name")]),
        ("vehicle_variants", [pk(),
                              sa.Column("model_id", sa.Integer, sa.ForeignKey("models.id", ondelete="CASCADE"), nullable=False),
                              sa.Column("market", sa.Text, nullable=False, server_default="Argentina"),
                              sa.Column("year_from", sa.Integer), sa.Column("year_to", sa.Integer),
                              sa.Column("version", sa.Text), sa.Column("engine", sa.Text),
                              sa.Column("fuel", sa.Text), sa.Column("drivetrain", sa.Text),
                              sa.Column("notes", sa.Text)]),
        ("transmissions", [pk(), sa.Column("manufacturer", sa.Text), sa.Column("code", sa.Text),
                           sa.Column("type", sa.Text), sa.Column("gears", sa.Integer),
                           sa.Column("notes", sa.Text)]),
        ("sources", [pk(), sa.Column("source_type", sa.Text, nullable=False),
                     sa.Column("publisher", sa.Text), sa.Column("title", sa.Text, nullable=False),
                     sa.Column("document_year", sa.Integer), sa.Column("url", sa.Text),
                     sa.Column("reference", sa.Text),
                     sa.Column("checked_at", sa.DateTime, server_default=now),
                     sa.Column("notes", sa.Text)]),
        ("vehicle_transmissions", [pk(),
                                   sa.Column("vehicle_variant_id", sa.Integer, sa.ForeignKey("vehicle_variants.id", ondelete="CASCADE"), nullable=False),
                                   sa.Column("transmission_id", sa.Integer, sa.ForeignKey("transmissions.id", ondelete="CASCADE"), nullable=False),
                                   sa.Column("validation_status", sa.Text, nullable=False, server_default="PENDING_REVIEW"),
                                   sa.Column("source_id", sa.Integer, sa.ForeignKey("sources.id")),
                                   sa.Column("notes", sa.Text),
                                   sa.UniqueConstraint("vehicle_variant_id", "transmission_id")]),
        ("fluids", [pk(), sa.Column("manufacturer", sa.Text), sa.Column("name", sa.Text),
                    sa.Column("specification", sa.Text), sa.Column("notes", sa.Text)]),
        ("transmission_fluid_data", [pk(),
                                     sa.Column("vehicle_transmission_id", sa.Integer, sa.ForeignKey("vehicle_transmissions.id", ondelete="CASCADE"), nullable=False),
                                     sa.Column("fluid_id", sa.Integer, sa.ForeignKey("fluids.id")),
                                     sa.Column("specification", sa.Text),
                                     sa.Column("total_capacity_l", sa.Float),
                                     sa.Column("service_capacity_l", sa.Float),
                                     sa.Column("level_check_method", sa.Text),
                                     sa.Column("validation_status", sa.Text, nullable=False, server_default="PENDING_REVIEW"),
                                     sa.Column("source_id", sa.Integer, sa.ForeignKey("sources.id")),
                                     sa.Column("notes", sa.Text)]),
        ("procedures", [pk(),
                        sa.Column("vehicle_transmission_id", sa.Integer, sa.ForeignKey("vehicle_transmissions.id", ondelete="CASCADE"), nullable=False),
                        sa.Column("procedure_type", sa.Text, nullable=False),
                        sa.Column("name", sa.Text, nullable=False),
                        sa.Column("description", sa.Text),
                        sa.Column("validation_status", sa.Text, nullable=False, server_default="PENDING_REVIEW"),
                        sa.Column("source_id", sa.Integer, sa.ForeignKey("sources.id"))]),
        ("procedure_steps", [pk(),
                             sa.Column("procedure_id", sa.Integer, sa.ForeignKey("procedures.id", ondelete="CASCADE"), nullable=False),
                             sa.Column("step_number", sa.Integer, nullable=False),
                             sa.Column("title", sa.Text, nullable=False),
                             sa.Column("instruction", sa.Text, nullable=False),
                             sa.Column("warning", sa.Text),
                             sa.Column("requires_confirmation", sa.Integer, nullable=False, server_default="1"),
                             sa.UniqueConstraint("procedure_id", "step_number")]),
        ("vins", [pk(),
                  sa.Column("vehicle_variant_id", sa.Integer, sa.ForeignKey("vehicle_variants.id", ondelete="CASCADE"), nullable=False),
                  sa.Column("vin", sa.Text, nullable=False, unique=True),
                  sa.Column("is_demo", sa.Integer, nullable=False, server_default="0")]),
        ("workshop_records", [pk(),
                              sa.Column("source_row", sa.Integer, nullable=False, unique=True),
                              sa.Column("legacy_id", sa.Text),
                              sa.Column("vehicle_description", sa.Text, nullable=False),
                              sa.Column("liters_used", sa.Float), sa.Column("atf_used", sa.Text),
                              sa.Column("filter_1", sa.Text), sa.Column("filter_2", sa.Text),
                              sa.Column("notes", sa.Text), sa.Column("original_status", sa.Text),
                              sa.Column("nishimoto_price", sa.Float),
                              sa.Column("liqui_moly_price", sa.Float),
                              sa.Column("motul_price", sa.Float),
                              sa.Column("valvoline_price", sa.Float),
                              sa.Column("mannol_price", sa.Float),
                              sa.Column("imported_at", sa.DateTime, server_default=now)]),
        ("technical_reference_records", [pk(),
                                         sa.Column("source_row", sa.Integer, nullable=False, unique=True),
                                         sa.Column("brand", sa.Text, nullable=False),
                                         sa.Column("model", sa.Text, nullable=False),
                                         sa.Column("engine", sa.Text),
                                         sa.Column("year_from", sa.Integer), sa.Column("year_to", sa.Integer),
                                         sa.Column("year_to_label", sa.Text),
                                         sa.Column("transmission_type", sa.Text),
                                         sa.Column("transmission_code", sa.Text),
                                         sa.Column("reference_liters", sa.Float),
                                         sa.Column("oem_specification", sa.Text),
                                         sa.Column("suggested_product", sa.Text),
                                         sa.Column("imported_at", sa.DateTime, server_default=now)]),
        ("consolidated_atf_data", [pk(),
                                   sa.Column("technical_reference_id", sa.Integer, sa.ForeignKey("technical_reference_records.id", ondelete="CASCADE"), nullable=False, unique=True),
                                   sa.Column("workshop_record_id", sa.Integer, sa.ForeignKey("workshop_records.id", ondelete="SET NULL")),
                                   sa.Column("match_confidence", sa.Text, nullable=False, server_default="SIN_COINCIDENCIA"),
                                   sa.Column("review_reason", sa.Text),
                                   sa.Column("validation_status", sa.Text, nullable=False, server_default="PENDING_REVIEW"),
                                   sa.Column("reviewed_at", sa.DateTime),
                                   sa.Column("reviewed_by", sa.Text),
                                   sa.Column("review_notes", sa.Text)]),
    ]


INDEXES = [
    ("idx_models_brand", "models", ["brand_id"]),
    ("idx_variants_model", "vehicle_variants", ["model_id"]),
    ("idx_vins_vin", "vins", ["vin"]),
    ("idx_workshop_vehicle", "workshop_records", ["vehicle_description"]),
    ("idx_reference_vehicle", "technical_reference_records", ["brand", "model", "engine"]),
    ("idx_consolidated_status", "consolidated_atf_data", ["validation_status"]),
]

REVIEW_COLUMNS = [("reviewed_at", sa.DateTime), ("reviewed_by", sa.Text), ("review_notes", sa.Text)]


def upgrade():
    inspector = sa.inspect(op.get_bind())
    existing = set(inspector.get_table_names())
    for name, columns in _tables():
        if name not in existing:
            op.create_table(name, *columns)
    for name, table, columns in INDEXES:
        if name not in {index["name"] for index in sa.inspect(op.get_bind()).get_indexes(table)}:
            op.create_index(name, table, columns)
    if "consolidated_atf_data" in existing:
        present = {column["name"] for column in inspector.get_columns("consolidated_atf_data")}
        for column, kind in REVIEW_COLUMNS:
            if column not in present:
                op.add_column("consolidated_atf_data", sa.Column(column, kind))


def downgrade():
    for name, _ in reversed(_tables()):
        op.drop_table(name)
