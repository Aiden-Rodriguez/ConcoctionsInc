from fastapi import APIRouter
import sqlalchemy
from src import database as db

router = APIRouter()


@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    """
    Each unique item combination must have only a single price.
    """
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT potion_sku, SUM(inventory) AS inventory_count
            FROM potion_info_table
            WHERE potion_sku IN ('red', 'green', 'blue', 'dark')
            GROUP BY potion_sku"""))
        rows = result.fetchall()

        num_green_potions = 0
        num_blue_potions = 0
        num_red_potions = 0
        num_dark_potions = 0

        for row in rows:
            potion_sku = row[0]
            inventory_count = row[1]
    
            if potion_sku == 'green':
                num_green_potions = inventory_count
            elif potion_sku == 'blue':
                num_blue_potions = inventory_count
            elif potion_sku == 'red':
                num_red_potions = inventory_count
            elif potion_sku == 'dark':
                num_dark_potions = inventory_count

        catalogue_list = []
        #current logic: list all potions of 4 major types
        #potion names are a temp implementation ; currently they just reflect what is called in the database
        #in the future call potions the following:
        # Potion_x-x-x-x where x is the amount of colored ml respectively
        if num_green_potions > 0:
            catalogue_list.append(
                {
                    "sku": "num_green_potions",
                    "name": "green potion",
                    "quantity": num_green_potions,
                    "price": 50,
                    "potion_type": [0, 100, 0, 0],
                })
        if num_red_potions > 0:
            catalogue_list.append(
                {
                    "sku": "num_red_potions",
                    "name": "red potion",
                    "quantity": num_red_potions,
                    "price": 50,
                    "potion_type": [100, 0, 0, 0],
                })
        if num_blue_potions > 0:
            catalogue_list.append(
                {
                    "sku": "num_blue_potions",
                    "name": "blue potion",
                    "quantity": num_blue_potions,
                    "price": 50,
                    "potion_type": [0, 0, 100, 0],
                })
        if num_dark_potions > 0:
            catalogue_list.append(
                {
                    "sku": "num_dark_potions",
                    "name": "dark potion",
                    "quantity": num_dark_potions,
                    "price": 50,
                    "potion_type": [0, 0, 0, 100],
                })
        return catalogue_list
