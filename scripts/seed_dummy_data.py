import random
from datetime import datetime, timedelta, timezone
import sys
import os

from sqlmodel import Session

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.db import engine, create_db_and_tables
from app.models.hardware import Hardware, StatusEnum, ModelEnum


CENTERS = [
    "North Campus",
    "South Campus",
    "East Campus",
    "West Campus",
    "HQ",
    "Remote",
    "Warehouse A",
    "Warehouse B",
    "Data Center 1",
    "Data Center 2",
    "Lab Alpha",
    "Lab Beta",
    "Field Ops",
]

ADMINS = [
    "alice",
    "bob",
    "charlie",
    "diana",
    "eve",
    "frank",
    "grace",
    "heidi",
    "ivan",
    "judy",
    "mallory",
    "oscar",
    "peggy",
    "trent",
    "victor",
    "walter",
]

ENDUSERS = [
    "John Smith",
    "Jane Doe",
    "Alex Johnson",
    "Maria Garcia",
    "Wei Chen",
    "Priya Patel",
    "Liam Brown",
    "Emma Wilson",
    "Noah Davis",
    "Olivia Martinez",
    "Ava Taylor",
    "Isabella Thomas",
    "Sophia Anderson",
    "Mia Moore",
    "Charlotte Jackson",
    "Amelia White",
    "James Harris",
    "Benjamin Clark",
    "Lucas Lewis",
    "Henry Lee",
]

MODELS = list(ModelEnum)
STATUSES = list(StatusEnum)

VENDORS = ["Dell", "HP", "Lenovo", "Apple", "Acer", "ASUS", "MSI", "Samsung"]
SERIES = ["ProBook", "ThinkPad", "Latitude", "EliteBook", "MacBook", "Veriton", "ProDesk", "OptiPlex"]


def random_mac() -> str:
    return ":".join(f"{random.randint(0, 255):02x}" for _ in range(6))


def random_ip() -> str:
    return f"{random.randint(10, 223)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"


def random_uuid() -> str:
    import uuid

    return str(uuid.uuid4())


def random_serial() -> str:
    prefix = random.choice(["SN", "SRL", "S/N"]).replace("/", "")
    return f"{prefix}-{random.randint(100000, 999999)}-{random.randint(1000, 9999)}"


def random_hostname(model: ModelEnum) -> str:
    model_prefix = {
        ModelEnum.Notebook: "nb",
        ModelEnum.MFF: "mff",
        ModelEnum.AllInOne: "aio",
        ModelEnum.Backpack: "bp",
        ModelEnum.DockingStation: "dock",
        ModelEnum.Monitor: "mon",
    }[model]
    return f"{model_prefix}-{random.randint(1000, 9999)}"


def random_comment() -> str:
    comments = [
        "New device",
        "Reimaged and updated",
        "Ready for deployment",
        "Needs repair",
        "Assigned for testing",
        "Returned from user",
        "Spare unit",
        "Under observation",
        "Replacement scheduled",
        "Awaiting parts",
        "To be decommissioned",
        "Pending QA",
    ]
    return random.choice(comments)


def random_ticket(prefix: str = "TKT") -> str:
    return f"{prefix}-{random.randint(100000, 999999)}"


def random_center() -> str:
    return random.choice(CENTERS)


def random_admin() -> str:
    return random.choice(ADMINS)


def random_enduser() -> str:
    return random.choice(ENDUSERS)


def random_vendor_model(model: ModelEnum) -> str:
    vendor = random.choice(VENDORS)
    series = random.choice(SERIES)
    return f"{vendor} {series}"


def random_timestamp(days_back: int = 365) -> datetime:
    now = datetime.now(timezone.utc)
    delta_days = random.randint(0, days_back)
    delta_seconds = random.randint(0, 86400)
    return now - timedelta(days=delta_days, seconds=delta_seconds)


def generate_hardware() -> Hardware:
    model = random.choice(MODELS)
    status = random.choice(STATUSES)

    created_at = random_timestamp(365)
    # updated_at should be at or after created_at
    updated_at = created_at + timedelta(days=random.randint(0, 60), seconds=random.randint(0, 86400))
    if updated_at > datetime.now(timezone.utc):
        updated_at = datetime.now(timezone.utc)

    shipped_at = None
    if status == StatusEnum.SHIPPED:
        # Shipped sometime after created_at
        shipped_at = created_at + timedelta(days=random.randint(0, 30))
        if shipped_at > updated_at:
            updated_at = shipped_at

    return Hardware(
        hostname=random_hostname(model),
        mac=random_mac() if random.random() < 0.85 else None,
        ip=random_ip() if random.random() < 0.85 else None,
        ticket=random_ticket("TKT") if random.random() < 0.6 else None,
        po_ticket=random_ticket("PO") if random.random() < 0.4 else None,
        uuid=random_uuid() if random.random() < 0.9 else None,
        center=random_center() if random.random() < 0.85 else None,
        serial_number=random_serial(),
        model=model,
        status=status,
        enduser=(
            random_enduser()
            if status in {StatusEnum.RESERVED, StatusEnum.SHIPPED, StatusEnum.COMPLETED} and random.random() < 0.8
            else None
        ),
        admin=random_admin(),
        comment=random_comment() if random.random() < 0.5 else None,
        missing=True if random.random() < 0.1 else False,
        created_at=created_at,
        updated_at=updated_at,
        shipped_at=shipped_at,
    )


def seed(count: int = 1000) -> None:
    create_db_and_tables()
    created = 0
    with Session(engine) as session:
        for _ in range(count):
            hw = generate_hardware()
            session.add(hw)
            created += 1
            if created % 200 == 0:
                session.commit()
        session.commit()
    print(f"Seeded {created} hardware records.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Seed dummy hardware data")
    parser.add_argument("--count", type=int, default=1000, help="Number of records to create (default: 1000)")
    args = parser.parse_args()

    seed(args.count)
