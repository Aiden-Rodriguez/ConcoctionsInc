from fastapi import APIRouter, Depends
from enum import Enum
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db

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
        else: # if no exist then go ahead and change the db!
            result = connection.execute(sqlalchemy.text("""SELECT num_green_ml,
                                                        num_red_ml,
                                                        num_blue_ml,
                                                        num_dark_ml,
                                                        potion_capacity 
                                                        FROM global_inventory"""))
            row = result.mappings().one()
        
            num_green_ml = row['num_green_ml']
            num_red_ml = row['num_red_ml']
            num_blue_ml = row['num_blue_ml']
            num_dark_ml = row['num_dark_ml']
            potion_capacity = row['potion_capacity']

            potions_to_insert = []

            for potion in potions_delivered:
                potion_type = potion.potion_type
                potion_quantity = potion.quantity
                red_cost = potion_type[0]*potion_quantity
                green_cost = potion_type[1]*potion_quantity
                blue_cost = potion_type[2]*potion_quantity
                dark_cost = potion_type[3]*potion_quantity
                potions_to_insert.append([potion_type, potion_quantity])

            print(potions_to_insert)


            connection.execute(sqlalchemy.text("""UPDATE global_inventory 
                                               SET num_green_ml = num_green_ml - :green_cost,
                                               num_red_ml = num_red_ml - :red_cost,
                                               num_blue_ml = num_blue_ml - :blue_cost,
                                               num_dark_ml = num_dark_ml - :dark_cost"""),
                                    {"green_cost": green_cost, "red_cost": red_cost, "blue_cost": blue_cost, "dark_cost": dark_cost})
            

            for potion in potions_to_insert:
                connection.execute(sqlalchemy.text("""UPDATE potion_info_table
                                                   SET inventory = inventory + :potions_to_add
                                                   WHERE potion_distribution = :potion_distribution
                                                   """),
                                                   {"potions_to_add": potion[1], "potion_distribution": potion[0]})
            
            
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
                connection.execute(sqlalchemy.text("""INSERT INTO potions
                                                   (potion_order_id, time_id, potion_type, quantity)
                                                   VALUES (:potion_order_id, :time_id, :potion_type, :quantity)
                                                   """),
                                                   {"potion_order_id": order_id, "time_id": time_id, "potion_type": potion[0], "quantity": potion[1]})
            
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
        result = connection.execute(sqlalchemy.text("""SELECT num_green_ml, num_red_ml, num_blue_ml, num_dark_ml, 
                                                    potion_capacity
                                                    FROM global_inventory"""))

        row = result.mappings().one()  # Using mappings to access the columns by name

        # Extract values from the row
        num_green_ml = row['num_green_ml']
        num_red_ml = row['num_red_ml']
        num_blue_ml = row['num_blue_ml']
        num_dark_ml = row['num_dark_ml']
        potion_capacity = row['potion_capacity']

        result = connection.execute(sqlalchemy.text("""SELECT SUM(inventory)
                                                    FROM potion_info_table"""))
        total_potion_amount = result.scalar()
    
        #implement support for many pots later

        result = connection.execute(sqlalchemy.text("""SELECT potion_distribution
                                                    FROM potion_info_table"""))
        
        distributions = result.mappings().all()

        # result = connection.execute(sqlalchemy.text("""SELECT day
        #                                                 FROM DATE
        #                                                 ORDER BY id DESC
        #                                                 LIMIT 1"""))
        # #whatever the day is
        # day = result.scalar()

        potion_list = []
    
        for potion_type in distributions:
            distribution_values = potion_type['potion_distribution']
            if 100 not in distribution_values: # mixed potion
                red_cost = distribution_values[0]
                green_cost = distribution_values[1]
                blue_cost = distribution_values[2]
                dark_cost = distribution_values[3]
                count = 15
                while red_cost <= num_red_ml and green_cost <= num_green_ml and blue_cost <= num_blue_ml and dark_cost <= num_dark_ml and total_potion_amount < potion_capacity and count < 15:
                    count += 1
                    num_red_ml -= red_cost
                    num_green_ml -= green_cost 
                    num_blue_ml -= blue_cost
                    num_dark_ml -= dark_cost
                    total_potion_amount += 1
                    add_or_increment_item(potion_list, {'potion_type': [red_cost, green_cost, blue_cost, dark_cost], 'quantity': 1})
            else: # full potion; just make 3 of them its like whatever you know
                count = 0
                red_cost = distribution_values[0]
                green_cost = distribution_values[1]
                blue_cost = distribution_values[2]
                dark_cost = distribution_values[3]
                while red_cost <= num_red_ml and green_cost <= num_green_ml and blue_cost <= num_blue_ml and dark_cost <= num_dark_ml and total_potion_amount < potion_capacity and count < 3:
                    count += 1
                    total_potion_amount += 1
                    num_red_ml -= red_cost
                    num_green_ml -= green_cost 
                    num_blue_ml -= blue_cost
                    num_dark_ml -= dark_cost
                    add_or_increment_item(potion_list, {'potion_type': [red_cost, green_cost, blue_cost, dark_cost], 'quantity': 1})
    
    return potion_list




if __name__ == "__main__":
    print(get_bottle_plan())