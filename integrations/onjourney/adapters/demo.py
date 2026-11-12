from copy import deepcopy

from django.db.models import Sum

TENANT = {
    "slug": "nusantara-journeys",
    "company_name": "Nusantara Journeys",
    "tagline": "Perjalanan bermakna, dipandu orang lokal.",
    "email": "halo@nusantara-journeys.example",
    "phone": "+62 812 0000 0000",
    "address": "Denpasar, Bali",
}

PRODUCTS = [
    {
        "id": 101,
        "slug": "bali-timur-pesisir-desa",
        "name": "Bali Timur: Pesisir & Desa",
        "location": "Karangasem, Bali",
        "duration": "3 hari 2 malam",
        "description": (
            "Menjelajah pesisir timur Bali, bertemu perajin lokal, dan menikmati "
            "ritme desa tanpa terburu-buru."
        ),
        "price": "2850000",
        "currency": "IDR",
        "capacity": 12,
        "is_seasonal": False,
        "is_po_allowed": True,
        "payment_term_percentages": ["50", "50"],
        "categories": ["Budaya", "Pesisir"],
        "facilities": {"hotel": True, "meals": True, "tickets": True, "transport": "Minibus"},
        "carbon_footprint": "18.4",
        "image": "images/bali-east.svg",
    },
    {
        "id": 102,
        "slug": "sumba-savana-kampung-adat",
        "name": "Sumba: Savana & Kampung Adat",
        "location": "Sumba Timur, NTT",
        "duration": "4 hari 3 malam",
        "description": (
            "Perjalanan kecil ke bentang savana, air terjun, dan kampung adat "
            "bersama pemandu dari Sumba."
        ),
        "price": "4750000",
        "currency": "IDR",
        "capacity": 10,
        "is_seasonal": False,
        "is_po_allowed": True,
        "payment_term_percentages": ["50", "50"],
        "categories": ["Alam", "Budaya"],
        "facilities": {"hotel": True, "meals": True, "tickets": True, "transport": "Minibus"},
        "carbon_footprint": "24.1",
        "image": "images/sumba.svg",
    },
    {
        "id": 201,
        "slug": "open-trip-labuan-bajo",
        "name": "Open Trip Labuan Bajo",
        "location": "Labuan Bajo, NTT",
        "duration": "3 hari 2 malam",
        "description": (
            "Keberangkatan kelompok kecil ke pulau sekitar Taman Nasional Komodo "
            "dengan jadwal yang terukur."
        ),
        "price": "3950000",
        "currency": "IDR",
        "capacity": 16,
        "is_seasonal": True,
        "is_po_allowed": True,
        "payment_term_percentages": ["30", "70"],
        "categories": ["Bahari", "Open trip"],
        "facilities": {"hotel": True, "meals": True, "tickets": True, "transport": "Kapal wisata"},
        "carbon_footprint": "21.7",
        "image": "images/labuan-bajo.svg",
    },
    {
        "id": 202,
        "slug": "bromo-kawah-ijen",
        "name": "Bromo & Kawah Ijen",
        "location": "Jawa Timur",
        "duration": "4 hari 3 malam",
        "description": (
            "Keberangkatan musiman ke lanskap vulkanik Jawa Timur bersama kelompok kecil."
        ),
        "price": "3250000",
        "currency": "IDR",
        "capacity": 12,
        "is_seasonal": True,
        "is_po_allowed": True,
        "payment_term_percentages": ["30", "70"],
        "categories": ["Pegunungan", "Open trip"],
        "facilities": {"hotel": True, "meals": True, "tickets": True, "transport": "Minibus"},
        "carbon_footprint": "19.8",
        "image": "images/bromo.svg",
    },
]

DEPARTURES = {
    201: [
        {
            "id": 2001,
            "tour_date": "2027-02-12",
            "capacity": 8,
            "remaining": 8,
            "po_deadline": "2027-01-20",
            "payment_completion_deadline": "2027-02-01",
        },
        {
            "id": 2002,
            "tour_date": "2027-03-19",
            "capacity": 2,
            "remaining": 2,
            "po_deadline": "2027-02-25",
            "payment_completion_deadline": "2027-03-05",
        },
    ],
    202: [
        {
            "id": 2101,
            "tour_date": "2027-04-09",
            "capacity": 10,
            "remaining": 10,
            "po_deadline": "2027-03-15",
            "payment_completion_deadline": "2027-03-29",
        }
    ],
}


class DemoClient:
    def get_tenant(self):
        return deepcopy(TENANT)

    def list_products(self):
        return deepcopy(PRODUCTS)

    def get_product(self, product_id):
        product = next((item for item in PRODUCTS if item["id"] == product_id), None)
        if product is None:
            raise KeyError(product_id)
        return deepcopy(product)

    def list_departures(self, product_id):
        from storefront.models import BookingReference

        departures = deepcopy(DEPARTURES.get(product_id, []))
        for departure in departures:
            reserved = (
                BookingReference.objects.filter(
                    product_id=product_id,
                    season_id=departure["id"],
                ).aggregate(total=Sum("guest_no"))["total"]
                or 0
            )
            departure["remaining"] = max(0, departure["remaining"] - reserved)
        return departures

    def get_departure(self, product_id, season_id):
        return next(
            (item for item in self.list_departures(product_id) if item["id"] == season_id),
            None,
        )
