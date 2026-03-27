# Amazon Return Policy Rules
# Based on Amazon's official return policy documentation
# Layer 1: Category and title keyword matching

# Keywords in the category path that strongly indicate NON-RETURNABLE
NON_RETURNABLE_CATEGORY_KEYWORDS = [
    # Hazmat
    "aerosol",
    "hazardous material",
    "dangerous good",
    "flammable",
    "explosive",
    "ammunition",
    "compressed gas",
    "pesticide",
    "herbicide",
    "fertilizer",
    "propane",
    "butane",
    "fuel cell",
    "toxic",
    "corrosive",
    "oxidizer",
    "radioactive",
    # Perishables / regulated
    "perishable",
    "live plant",
    "live animal",
    "fresh food",
    "grocery",
    # Digital
    "downloadable",
    "digital download",
    "gift card",
    "e-gift",
    "software",
    # Pest control (within any category)
    "fly & mosquito control",
    "fly repellent",
    "insect control",
    "flea & tick",
]

# Keywords in product title that suggest hazmat / non-returnable
NON_RETURNABLE_TITLE_KEYWORDS = [
    # Hazmat / flammable
    "aerosol",
    "flammable",
    "hazmat",
    "propane",
    "butane",
    "compressed gas",
    "explosive",
    "ammunition",
    "ammo",
    "corrosive",
    "oxidizer",
    "spray can",
    "pressurized",
    "regulated by dot",
    "hazardous",
    "dangerous goods",
    "lithium battery",
    "lithium batteries",
    "paint thinner",
    "solvent",
    "acetone",
    "isopropyl alcohol",
    "rubbing alcohol",
    # Explicitly marked
    "non-returnable",
    "not returnable",
    # Pesticides / insecticides (EPA regulated)
    "fly spray",
    "fly repellent",
    "insecticide",
    "pesticide",
    "herbicide",
    "mosquito repellent",
    "insect repellent",
    "bug spray",
    "emulsifiable concentrate",
    "repel-x",
    # Pharmaceutical / medical
    "ophthalmic",
    "ointment",
    "medicated",
    "veterinary",
    # Liquid consumables (can't verify once opened)
    "mink oil",
    "linseed oil",
    "neatsfoot oil",
    "liquid concentrate",
]

# Top-level Amazon categories that are definitively NON-RETURNABLE
NON_RETURNABLE_TOP_CATEGORIES = [
    "software",
    "gift cards",
    "digital music",
    "kindle store",
    "amazon grocery",
    "grocery & gourmet food",
    "fresh",
]

# Top-level Amazon categories that are GENERALLY RETURNABLE
# (exceptions apply if product is hazmat — checked separately)
GENERALLY_RETURNABLE_TOP_CATEGORIES = [
    "electronics",
    "computers & accessories",
    "computers",
    "clothing, shoes & jewelry",
    "clothing",
    "shoes",
    "toys & games",
    "sports & outdoors",
    "office products",
    "books",
    "baby",
    "baby products",
    "automotive",
    "musical instruments",
    "arts, crafts & sewing",
    "cell phones & accessories",
    "health & household",
    "beauty & personal care",
    "pet supplies",
    "tools & home improvement",
    "home improvement",
    "home & kitchen",
    "kitchen & dining",
    "furniture",
    "garden & outdoor",
    "luggage & travel gear",
    "handmade products",
    "collectibles & fine art",
    "industrial & scientific",
]
