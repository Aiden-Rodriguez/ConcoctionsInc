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
            SELECT potion_sku, SUM(inventory) AS inventory_count, price, potion_distribution
            FROM potion_info_table
            WHERE inventory >= 1 
            GROUP BY potion_sku, price, potion_distribution, priority
            ORDER BY priority desc"""))
        rows = result.mappings().all()

        # append stuff to see whats in inventory
        potion_in_inventory = []
        for row in rows:
            potion_sku = row['potion_sku']
            potion_name = row['potion_sku']
            inventory_count = row['inventory_count']
            price = row['price']
            potion_distribution = row['potion_distribution']
            potion_in_inventory.append(
                {
                    "sku": potion_sku,
                    "name": potion_name,
                    "quantity": inventory_count,
                    "price": price,
                    "potion_type": potion_distribution
                }
            )

        result = connection.execute(sqlalchemy.text("""SELECT day
                                                        FROM DATE
                                                        ORDER BY id DESC
                                                        LIMIT 1"""))
        #whatever the day is
        day = result.scalar()

        print(potion_in_inventory)

        catalogue_list = []
        potions_to_remove = []
        
        for potion_type in potion_in_inventory:
            if day == "Edgeday":
                if potion_type['potion_type'][0] == 0:
                    catalogue_list.append(potion_type)
                    potions_to_remove.append(potion_type)
            elif day == "Arcanaday":
                if potion_type['potion_type'][2] == 0:
                    catalogue_list.append(potion_type)
                    potions_to_remove.append(potion_type)
            elif day == "Bloomday":
                if potion_type['potion_type'][1] == 0:
                    catalogue_list.append(potion_type)
                    potions_to_remove.append(potion_type)

            potion_in_inventory = [p for p in potion_in_inventory if p not in potions_to_remove]

            #just start adding potions if no special day or if slots remain!
            while len(catalogue_list) < 6 and len(potion_in_inventory) > 0:
                potion_type = potion_in_inventory.pop(0)
                catalogue_list.append(potion_type)

        return catalogue_list
