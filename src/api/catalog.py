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
            SELECT potion_sku, SUM(inventory) AS inventory_count, price, potion_distribution, "1g_strat"
            FROM potion_info_table
            WHERE inventory >= 1 
            GROUP BY potion_sku, price, potion_distribution, priority, "1g_strat"
            ORDER BY priority desc"""))
        rows = result.mappings().all()

        # append stuff to see whats in inventory
        potion_in_inventory = []
        for row in rows:
            #invalid potion
            potion_sku = row['potion_sku']
            potion_name = row['potion_sku']
            inventory_count = row['inventory_count']
            price = row['price']
            potion_distribution = row['potion_distribution']
            one_g_strat = row['1g_strat']
            potion_in_inventory.append(
                {
                    "sku": potion_sku,
                    "name": potion_name,
                    "quantity": inventory_count,
                    "price": price,
                    "potion_type": [
                        potion_distribution[0],
                        potion_distribution[1],
                        potion_distribution[2],
                        potion_distribution[3]
                    ],
                    "1g_strat": one_g_strat
                }
            )



        result = connection.execute(sqlalchemy.text("""SELECT day
                                                        FROM DATE
                                                        ORDER BY id DESC
                                                        LIMIT 1"""))
        #whatever the day is
        day = result.scalar()

        catalogue_list = []
        #potions_to_remove = []
        added_skus = set()
        for potion_type in potion_in_inventory:

            one_g_strat = potion_type["1g_strat"]
            #remake list w/o the strat for the return
            potion_entry = {key: potion_type[key] for key in potion_type if key != "1g_strat"}
            #inflate ratings on new potion :)
            if one_g_strat == False:
                potion_entry['quantity'] = 1
                potion_entry['price'] = 1
                if potion_entry['sku'] not in added_skus:
                    catalogue_list.append(potion_entry)
                    added_skus.add(potion_entry['sku'])
                
            elif (day == "Edgeday" and potion_type['potion_type'][0] != 100) or \
                (day == "Arcanaday" and potion_type['potion_type'][2] != 100) or \
                (day == "Bloomday" and potion_type['potion_type'][1] != 100):

                #check for duplicates before appending
                if potion_entry['sku'] not in added_skus:
                    catalogue_list.append(potion_entry)
                    added_skus.add(potion_entry['sku'])

        #potion_in_inventory = [p for p in potion_in_inventory if p not in potions_to_remove]
        while len(catalogue_list) < 6 and len(potion_in_inventory) > 0:
            potion_entry = potion_in_inventory.pop(0)
            potion_entry = {key: potion_type[key] for key in potion_entry if key != "1g_strat"}

            if potion_entry['sku'] not in added_skus:
                catalogue_list.append(potion_entry)
                added_skus.add(potion_entry['sku'])

        return catalogue_list
