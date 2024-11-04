from fastapi import APIRouter
import sqlalchemy
from src import database as db
from src.api.inventory import get_gold_quan, get_ml_quan, get_potion_quan

router = APIRouter()


@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    """
    Each unique item combination must have only a single price.
    """
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("""
                                                    SELECT potion_sku, 
                                                    price, potion_distribution, "1g_strat", id
                                                    FROM potion_info_table
                                                    GROUP BY potion_sku, price, potion_distribution, priority, "1g_strat", id
                                                    ORDER BY priority desc"""))
        rows = result.mappings().all()


        result = connection.execute(sqlalchemy.text("""SELECT reset_timestamp
                                                        FROM global_inventory"""))
        reset_timestamp = result.scalar()

        potion_quan = get_potion_quan(connection, reset_timestamp)

        # append stuff to see whats in inventory
        potion_in_inventory = []
        for row in rows:
            for potion_type in potion_quan:
                #matching ids meaning quantity > 0
                if row['id'] == potion_type['potion_id']:
                    potion_sku = row['potion_sku']
                    potion_name = row['potion_sku']
                    inventory_count = potion_type['quantity']
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
        
        # print(potion_quan)
        print(potion_in_inventory)

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
                print("Bruh2")
                #check for duplicates before appending
                if potion_entry['sku'] not in added_skus:
                    catalogue_list.append(potion_entry)
                    added_skus.add(potion_entry['sku'])

        #potion_in_inventory = [p for p in potion_in_inventory if p not in potions_to_remove]
        while len(catalogue_list) < 6 and len(potion_in_inventory) > 0:
            potion_entry = potion_in_inventory.pop(0)
            potion_entry = {key: potion_entry[key] for key in potion_entry if key != "1g_strat"}

            if potion_entry['sku'] not in added_skus:
                catalogue_list.append(potion_entry)
                added_skus.add(potion_entry['sku'])

        #return catalogue_list
        return[
            {
            "sku": "bard_test_1",
            "name": "bard_test_1",
            "quantity": 99,
            "price": 30,
            "potion_type": [
            30,0,30,40
            ]
            },
            {
            "sku": "bard_test_2",
            "name": "bard_test_2",
            "quantity": 99,
            "price": 35,
            "potion_type": [
            25,0,25,50
            ]
            },
            {
            "sku": "bard_test_3",
            "name": "bard_test_3",
            "quantity": 99,
            "price": 30,
            "potion_type": [
            35,0,35,30
            ]
            },
            {
            "sku": "bard_test_4",
            "name": "bard_test_4",
            "quantity": 99,
            "price": 30,
            "potion_type": [
            40,0,40,20
            ]
            },
            {
            "sku": "bard_test_5",
            "name": "bard_test_5",
            "quantity": 99,
            "price": 30,
            "potion_type": [
            30,0,45,25
            ]
            },
            {
            "sku": "bard_test_6",
            "name": "bard_test_6",
            "quantity": 99,
            "price": 30,
            "potion_type": [
            30,0,32,38
            ]
            }
            ]