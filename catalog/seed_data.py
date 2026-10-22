# Sample catalog data. Styling suggestions are entered by hand, not computed.

TONES = [f"Tone {i}" for i in range(1, 11)]

# card code -> tone number
CARDS = {
    "ST-12": 1,
    "ST-14": 2,
    "ST-08": 3,
    "ST-07": 4,
    "ST-09": 4,
    "ST-04": 5,
    "ST-01": 6,
    "ST-02": 7,
    "ST-06": 8,
    "ST-03": 9,
    "ST-11": 9,
    "ST-05": 10,
}

# (name, slug), in display order
FAMILIES = [
    ("Red", "red"),
    ("Maroon", "maroon"),
    ("Pink", "pink"),
    ("Orange", "orange"),
    ("Yellow", "yellow"),
    ("Green", "green"),
    ("Blue", "blue"),
    ("Purple", "purple"),
    ("Brown", "brown"),
    ("Neutrals", "neutrals"),
]

SHADES = {
    "Red": [
        ("Coral Red", "#E8574A"), ("Tomato", "#E0452F"), ("Scarlet", "#D62718"),
        ("Rose Red", "#D9455F"), ("Cherry", "#C8102E"), ("Crimson", "#B0182F"),
        ("Brick Red", "#A83232"), ("Chilli", "#9B1C1C"),
    ],
    "Maroon": [
        ("Raspberry", "#A63A5C"), ("Cranberry", "#8A2A3B"), ("Classic Maroon", "#800000"),
        ("Wine", "#722F37"), ("Burgundy", "#6D1A36"), ("Rosewood", "#65000B"),
        ("Mulberry", "#5E2750"), ("Oxblood", "#4A0404"),
    ],
    "Pink": [
        ("Baby Pink", "#F4C2D0"), ("Blush", "#E8B4B8"), ("Salmon Pink", "#F08A8A"),
        ("Dusty Pink", "#C9929C"), ("Rose", "#D96C8A"), ("Hot Pink", "#E6338F"),
        ("Fuchsia", "#C2185B"), ("Deep Magenta", "#A3124E"),
    ],
    "Orange": [
        ("Peach", "#F9C5A0"), ("Apricot", "#F5A25D"), ("Marigold", "#F6A21E"),
        ("Saffron", "#F58220"), ("Burnt Orange", "#CC5500"), ("Terracotta", "#C1633F"),
        ("Rust", "#B7410E"), ("Dark Rust", "#8F3B12"),
    ],
    "Yellow": [
        ("Butter", "#F5E6A3"), ("Lemon", "#F2E34C"), ("Canary", "#FFD93B"),
        ("Sunflower", "#F4C430"), ("Honey", "#E8B84A"), ("Golden", "#DAA520"),
        ("Mustard", "#C8961A"), ("Ochre", "#A67C1D"),
    ],
    "Green": [
        ("Mint", "#A8D8B9"), ("Pista", "#B9D6A0"), ("Sage", "#8FA58A"),
        ("Emerald", "#1E8C5A"), ("Sea Green", "#3C9D8F"), ("Teal", "#0E7C86"),
        ("Olive", "#6B7A2E"), ("Bottle Green", "#0B5D3B"),
    ],
    "Blue": [
        ("Powder Blue", "#B5D0E8"), ("Sky Blue", "#87BFE8"), ("Cerulean", "#2A7DB8"),
        ("Peacock Blue", "#0F6E8C"), ("Royal Blue", "#2B50AA"), ("Denim", "#3B5F8A"),
        ("Indigo", "#3F3F8F"), ("Navy", "#1B2A4A"),
    ],
    "Purple": [
        ("Lavender", "#B7A6D9"), ("Lilac", "#C3A9D6"), ("Orchid", "#A870B5"),
        ("Mauve", "#A27A9A"), ("Violet", "#7B4FA6"), ("Royal Purple", "#5B2D8E"),
        ("Plum", "#6E3A6E"), ("Aubergine", "#4B2A4F"),
    ],
    "Brown": [
        ("Fawn", "#C8A27A"), ("Tan", "#B08968"), ("Camel", "#A67B5B"),
        ("Caramel", "#A9702F"), ("Mocha", "#8B6B4F"), ("Cocoa", "#6F4E37"),
        ("Coffee", "#5C4033"), ("Chocolate", "#4B2E1E"),
    ],
    "Neutrals": [
        ("Off White", "#F5F1E8"), ("Cream", "#F3E9D2"), ("Beige", "#D9C7A8"),
        ("Sand", "#C2B280"), ("Light Grey", "#D3D3D3"), ("Steel Grey", "#71797E"),
        ("Charcoal", "#36454F"), ("Jet Black", "#0B0B0B"),
    ],
}

BOTTOM_TYPES = [
    ("Jeans", "jeans"),
    ("Trousers", "trousers"),
    ("Chinos", "chinos"),
    ("Pyjama", "pyjama"),
]

BOTTOM_COLORS = [
    ("Black", "#111111"), ("Charcoal", "#36454F"), ("Navy", "#1B2A4A"),
    ("Indigo Denim", "#2F4A73"), ("Light Blue Denim", "#7C9CBF"), ("Khaki", "#B8A67A"),
    ("Beige", "#D8C8A8"), ("Olive", "#5B6236"), ("Off White", "#EFEBE0"),
    ("Brown", "#5C4033"),
]

# (name, slug, has_pairing)
GARMENTS = [
    ("Shirt", "shirt", True),
    ("T-shirt", "t-shirt", True),
    ("Men's Kurta", "mens-kurta", True),
    ("Women's Kurta", "womens-kurta", False),
    ("Saree", "saree", False),
    ("Suit", "suit", False),
    ("Jeans", "jeans", False),
    ("Pants", "pants", False),
]

# garment slug -> bottom type slugs
GARMENT_BOTTOMS = {
    "shirt": ["jeans", "trousers", "chinos"],
    "t-shirt": ["jeans", "trousers", "chinos"],
    "mens-kurta": ["pyjama"],
}

DEMO_SHOP = {"name": "Demo Shop", "code": "SH-014", "slug": "sh-014", "city": "Demo City"}