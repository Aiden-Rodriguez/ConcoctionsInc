from fastapi import APIRouter
import sqlalchemy
from src import database as db
from src.api.inventory import get_gold_quan, get_ml_quan, get_potion_quan
import random

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
        #print(potion_in_inventory)


        result = connection.execute(sqlalchemy.text("""SELECT day, time
                                                        FROM DATE
                                                        ORDER BY id DESC
                                                        LIMIT 1"""))
        #whatever the day is
        row = result.mappings().one()
        day = row['day']
        time = row['time']


        #manage priorities of potions based on day
        result = connection.execute(sqlalchemy.text("""SELECT 
                                                    potion_info_table.potion_sku as potion_sku,
                                                    potion_id,
                                                    best_days,
                                                    secondary_pick,
                                                    optimal_potion_timing.for_class,
                                                    time_range
                                                    FROM
                                                    optimal_potion_timing
                                                    JOIN potion_info_table ON potion_info_table.id = optimal_potion_timing.potion_id
                                                    """))
        rows = result.mappings().all()
        primary_list = []
        secondary_list = []
        for row in rows:
            potion_sku = row['potion_sku']
            potion_id = row['potion_id']
            best_days = row['best_days']
            secondary_pick = row['secondary_pick']
            for_class = row['for_class']
            time_range = row['time_range']

            #if the day is right, and in inventory put it in high priority, or secondary
            if day in best_days:
                for potion in potion_in_inventory:
                    if potion['sku'] == potion_sku:
                        primary_list.append(potion)
            if day in secondary_pick:
                for potion in potion_in_inventory:
                    if potion['sku'] == potion_sku:
                        secondary_list.append(potion)

                        
        
        catalogue_list = []

        #print(primary_list)
        #print(secondary_list)

        #primary list appends up to 6 items of high priority
        for potion_type in primary_list:
            one_g_strat = potion_type["1g_strat"]
            potion_sku = potion_type['sku']
            potion_entry = {key: potion_type[key] for key in potion_type if key != "1g_strat"}

            if one_g_strat == False:
                potion_entry['quantity'] = 1
                potion_entry['price'] = 1
            # if rogue or barbarian. i know hardcoding this is bad but it would be a pain otherwise and im only doing this to 2 classes
            if potion_sku == "trogolodyte food":
                if time >= 10 and time <= 20:
                    catalogue_list.append(potion_entry)  
            elif potion_sku == "sneaky sneaky":
                if time >= 22 or (time >= 0 and time <= 8):
                    catalogue_list.append(potion_entry)            
            else:
                catalogue_list.append(potion_entry)
            
        #secondary list happens when not all primary gets filled, but some level of priority is there still
        random.shuffle(secondary_list)
        for potion_type in secondary_list:
            one_g_strat = potion_type["1g_strat"]
            potion_sku = potion_type['sku']
            potion_entry = {key: potion_type[key] for key in potion_type if key != "1g_strat"}

            if one_g_strat == False:
                potion_entry['quantity'] = 1
                potion_entry['price'] = 1
            
            if len(catalogue_list) < 6:
                catalogue_list.append(potion_entry)
        
        #if we got nothing else with any priority ;(
        last_ditch_effort = []
        for potion_type in potion_in_inventory:
            if potion_type not in primary_list and potion_type not in secondary_list:
                last_ditch_effort.append(potion_type)

        random.shuffle(last_ditch_effort)
        for potion_type in last_ditch_effort:
            one_g_strat = potion_type["1g_strat"]
            potion_sku = potion_type['sku']
            potion_entry = {key: potion_type[key] for key in potion_type if key != "1g_strat"}

            if one_g_strat == False:
                potion_entry['quantity'] = 1
                potion_entry['price'] = 1

            if len(catalogue_list) < 6:
                catalogue_list.append(potion_entry)

        return catalogue_list
        # return[
        #     {
        #     "sku": "rogue_test_1",
        #     "name": "rogue_test_1",
        #     "quantity": 99,
        #     "price": 30,
        #     "potion_type": [
        #     20,20,10,50
        #     ]
        #     },
        #     {
        #     "sku": "rogue_test_2",
        #     "name": "rogue_test_2",
        #     "quantity": 99,
        #     "price": 30,
        #     "potion_type": [
        #     25,25,10,40
        #     ]
        #     },
        #     {
        #     "sku": "rogue_test_3",
        #     "name": "rogue_test_3",
        #     "quantity": 99,
        #     "price": 30,
        #     "potion_type": [
        #     0,0,50,50
        #     ]
        #     },
        #     {
        #     "sku": "rogue_test_4WL",
        #     "name": "rogue_test_4WL",
        #     "quantity": 99,
        #     "price": 30,
        #     "potion_type": [
        #     20,20,30,30
        #     ]
        #     },
        #     {
        #     "sku": "rogue_test_5",
        #     "name": "rogue_test_5",
        #     "quantity": 99,
        #     "price": 30,
        #     "potion_type": [
        #     25,0,25,50
        #     ]
        #     },
        #     {
        #     "sku": "rogue_test_6R",
        #     "name": "rogue_test_6R",
        #     "quantity": 99,
        #     "price": 30,
        #     "potion_type": [
        #     0,25,25,50
        #     ]
        #     }
        #     ]
        
        # return[
        #     {
        #     "sku": "monk_test_1",
        #     "name": "monk_test_1",
        #     "quantity": 99,
        #     "price": 30,
        #     "potion_type": [
        #     25,25,25,25
        #     ]
        #     },
        #     {
        #     "sku": "monk_test_2",
        #     "name": "monk_test_2",
        #     "quantity": 99,
        #     "price": 30,
        #     "potion_type": [
        #     35,35,30,0
        #     ]
        #     },
        #     {
        #     "sku": "monk_test_3",
        #     "name": "monk_test_3",
        #     "quantity": 99,
        #     "price": 30,
        #     "potion_type": [
        #     35,30,35,0
        #     ]
        #     },
        #     {
        #     "sku": "monk_test_4",
        #     "name": "monk_test_4",
        #     "quantity": 99,
        #     "price": 30,
        #     "potion_type": [
        #     30,35,35,0
        #     ]
        #     },
        #     {
        #     "sku": "monk_test_5",
        #     "name": "monk_test_5",
        #     "quantity": 99,
        #     "price": 30,
        #     "potion_type": [
        #     30,45,25,0
        #     ]
        #     },
        #     {
        #     "sku": "monk_test_6",
        #     "name": "monk_test_6",
        #     "quantity": 99,
        #     "price": 30,
        #     "potion_type": [
        #     40,40,20,0
        #     ]
        #     }
        #     ]