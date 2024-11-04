from fastapi import APIRouter, Depends
from enum import Enum
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db
from src.api.inventory import get_gold_quan, get_ml_quan, get_potion_quan

router = APIRouter(
    prefix="/bottler",
    tags=["bottler"],
    dependencies=[Depends(auth.get_api_key)],
)

class PotionInventory(BaseModel):
    potion_type: list[int]
    quantity: int

@router.post("/deliver/{order_id}")
def post_deliver_bottles(potions_delivered: list[PotionInventory], order_id: int):
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("""SELECT EXISTS
                                                    (SELECT 1 FROM potion_order_table 
                                                    WHERE potion_order_id = :potion_order_id)"""), 
                                    {"potion_order_id": order_id})
        #if the row exists, this transaction has already happened!! bad!
        row = result.scalar()
        if row == True:
            return "OK"
        else: 

            potions_to_insert = []

            red_cost = 0
            green_cost = 0
            blue_cost = 0
            dark_cost = 0

            for potion in potions_delivered:
                potion_type = potion.potion_type
                potion_quantity = potion.quantity
                red_cost += potion_type[0]*potion_quantity
                green_cost += potion_type[1]*potion_quantity
                blue_cost += potion_type[2]*potion_quantity
                dark_cost += potion_type[3]*potion_quantity
                potions_to_insert.append([potion_type, potion_quantity])

            print(potions_to_insert)
            
            
            connection.execute(sqlalchemy.text("""INSERT INTO potion_order_table 
                                               (potion_order_id)
                                               VALUES (:potion_order_id)"""),
               {"potion_order_id": order_id})  


            result = connection.execute(sqlalchemy.text("""SELECT id
                                                        FROM DATE
                                                        ORDER BY id DESC
                                                        LIMIT 1"""))
            time_id = result.scalar()

            for potion in potions_to_insert:
                potion_type = potion[0]
                potion_quantity = potion[1]

                connection.execute(sqlalchemy.text("""INSERT INTO potions
                                                   (potion_order_id, time_id, potion_type, quantity)
                                                   VALUES (:potion_order_id, :time_id, :potion_type, :quantity)
                                                   """),
                                                   {"potion_order_id": order_id, "time_id": time_id, "potion_type": potion[0], "quantity": potion[1]})

                result = connection.execute(sqlalchemy.text("""SELECT id
                                                   FROM potion_info_table
                                                   WHERE potion_distribution = :dist"""),
                                                   {"dist": potion_type})
                potion_id = result.scalar()
                red_change = potion_type[0]*potion_quantity
                green_change = potion_type[1]*potion_quantity
                blue_change = potion_type[2]*potion_quantity
                dark_change = potion_type[3]*potion_quantity
                connection.execute(sqlalchemy.text("""INSERT INTO ledger_transactions
                                                    (exchange_type, linking_id, potion_id, potion_quantity, red_ml_change, green_ml_change, blue_ml_change, dark_ml_change)
                                                    VALUES ('Potion Create', :id, :potion_id, :potion_quantity, :red_change, :green_change, :blue_change, :dark_change)
                                                    """),
                                                    {"id": order_id, "potion_id": potion_id, "potion_quantity": potion[1], "red_change": -1*red_change, "green_change": -1*green_change, "blue_change": -1*blue_change, "dark_change": -1*dark_change})
            
            print(f"potions delievered: {potions_delivered} order_id: {order_id}")
            return "OK"

#deal with adding dictionary stuff
def add_or_increment_item(item_list, new_item):
    for item in item_list:
        #check if the item with the same sku already exists
        if item['potion_type'] == new_item['potion_type']:
            #increment the quantity by the value of the new item
            item['quantity'] += new_item['quantity']
            return

    #if the item does not exist, add it to the list
    item_list.append(new_item)

@router.post("/plan")
def get_bottle_plan():
    """
    Go from barrel to bottle.
    """
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("""SELECT
                                                    potion_capacity, reset_timestamp
                                                    FROM global_inventory"""))

        row = result.mappings().one() 

        potion_capacity = row['potion_capacity']
        reset_timestamp = row['reset_timestamp']

        gold = get_gold_quan(connection, reset_timestamp)
        ml_quan = get_ml_quan(connection, reset_timestamp)

        num_red_ml = ml_quan[0]
        num_green_ml = ml_quan[1]
        num_blue_ml = ml_quan[2]
        num_dark_ml = ml_quan[3]

        potion_quans = get_potion_quan(connection, reset_timestamp)

        total_potion_amount = 0
        for potion in potion_quans:
            total_potion_amount += potion['quantity']

        result = connection.execute(sqlalchemy.text("""SELECT potion_distribution,
                                                    in_test, id
                                                    FROM potion_info_table
                                                    ORDER BY priority desc"""))
        #potions will come based on highest priority
        #0 priority on a potion means we wont make it / 111 as 5th element in type

        #list of all potions in db that are avail
        distributions = result.mappings().all()

        #match ledger values to dist values. if no value exists then its just 0

        updated_dist = []

        for potion_type in distributions:
            potion_dict = dict(potion_type)
            match = False
            for type in potion_quans:
                if potion_dict['id'] == type['potion_id']:
                    potion_dict['inventory'] = type['quantity']
                    match = True
                    break
            if not match:
                potion_dict['inventory'] = 0
    
            updated_dist.append(potion_dict)

        #print(updated_dist)

        potion_list = []

        # make # of potions ; vary on capacity
        #check if we are in early game; if so dont mix
        if total_potion_amount <= 10 and gold <= 500:
            eg_check = True
        else:
            eg_check = False
        
        #print(eg_check)

        updated_dist = [potion for potion in updated_dist if 111 not in potion['potion_distribution']]

        print(updated_dist)

        #floodfill type beat
        while len(updated_dist) != 0:
            updated_dist = sorted(updated_dist, key=lambda potion: potion['inventory'])
            potion_type = updated_dist[0]
            inventory_value = potion_type['inventory']            
            distribution_values = potion_type['potion_distribution']

            red_cost = distribution_values[0]
            green_cost = distribution_values[1]
            blue_cost = distribution_values[2]
            dark_cost = distribution_values[3]
            if 100 not in distribution_values and eg_check != True: #earlygame check
                if red_cost <= num_red_ml and green_cost <= num_green_ml and blue_cost <= num_blue_ml and dark_cost <= num_dark_ml and total_potion_amount < potion_capacity and inventory_value < (12 + 4*(potion_capacity/50)):
                    num_red_ml -= red_cost
                    num_green_ml -= green_cost 
                    num_blue_ml -= blue_cost
                    num_dark_ml -= dark_cost
                    total_potion_amount += 1
                    #update inventory value for resorting
                    updated_dist[0]['inventory'] += 1
                    add_or_increment_item(potion_list, {'potion_type': [red_cost, green_cost, blue_cost, dark_cost], 'quantity': 1})
                else: #if we cannot afford making it, then dont deal with it
                    updated_dist.pop(0)
            elif 100 in distribution_values:
                if red_cost <= num_red_ml and green_cost <= num_green_ml and blue_cost <= num_blue_ml and dark_cost <= num_dark_ml and total_potion_amount < potion_capacity and inventory_value < (12 + 4*(potion_capacity/50)):
                    num_red_ml -= red_cost
                    num_green_ml -= green_cost 
                    num_blue_ml -= blue_cost
                    num_dark_ml -= dark_cost
                    total_potion_amount += 1
                    #update inventory value for resorting
                    updated_dist[0]['inventory'] += 1
                    add_or_increment_item(potion_list, {'potion_type': [red_cost, green_cost, blue_cost, dark_cost], 'quantity': 1})
                else:
                    updated_dist.pop(0)
            else:
                updated_dist.pop(0)
    
    return potion_list




if __name__ == "__main__":
    print(get_bottle_plan())