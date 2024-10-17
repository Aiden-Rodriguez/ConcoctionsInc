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
            row = result.mappings().one()  # Using mappings to access the columns by name

            # Extract values from the row
        
            num_green_ml = row['num_green_ml']
            num_red_ml = row['num_red_ml']
            num_blue_ml = row['num_blue_ml']
            num_dark_ml = row['num_dark_ml']
            potion_capacity = row['potion_capacity']

            pot_r = 0
            pot_b = 0
            pot_g = 0
            pot_d = 0

            potions_to_insert = []
            for potion in potions_delivered :
                if potion.potion_type == [0, 100, 0, 0]:
                    num_green_ml = num_green_ml - 100*potion.quantity
                    pot_r = potion.quantity
                    potions_to_insert.append(([100,0,0,0], potion.quantity)) 
                elif potion.potion_type == [100, 0, 0, 0] :
                    num_red_ml = num_red_ml - 100*potion.quantity
                    pot_g = potion.quantity
                    potions_to_insert.append(([0,100,0,0], potion.quantity)) 
                elif potion.potion_type == [0, 0, 100, 0] :
                    num_blue_ml = num_blue_ml - 100*potion.quantity
                    pot_b = potion.quantity
                    potions_to_insert.append(([0,0,100,0], potion.quantity)) 
                elif potion.potion_type == [0, 0, 0, 100] :
                    num_dark_ml = num_dark_ml - 100*potion.quantity
                    pot_d = potion.quantity
                    potions_to_insert.append(([0,0,0,100], potion.quantity)) 
            connection.execute(sqlalchemy.text("""UPDATE global_inventory 
                                               SET num_green_ml = :num_green_ml,
                                               num_red_ml = :num_red_ml,
                                               num_blue_ml = :num_blue_ml,
                                               num_dark_ml = :num_dark_ml"""),
                                    {"num_green_ml": num_green_ml, "num_red_ml": num_red_ml, "num_blue_ml": num_blue_ml, "num_dark_ml": num_dark_ml})
            
            #kinda monkey mode but it works for now
            connection.execute(sqlalchemy.text("""
                UPDATE potion_info_table 
                    SET inventory = inventory + CASE 
                    WHEN potion_sku = 'red' THEN :num_red_potions_bought 
                    WHEN potion_sku = 'green' THEN :num_green_potions_bought 
                    WHEN potion_sku = 'blue' THEN :num_blue_potions_bought 
                    WHEN potion_sku = 'dark' THEN :num_dark_potions_bought 
                    ELSE 0 
                END
                WHERE potion_sku IN ('red', 'green', 'blue', 'dark')"""), 
                {"num_red_potions_bought": pot_r, "num_green_potions_bought": pot_g, "num_blue_potions_bought": pot_b, "num_dark_potions_bought": pot_d})
            
            connection.execute(sqlalchemy.text("""INSERT INTO potion_order_table 
                                               (potion_order_id)
                                               VALUES (:potion_order_id)"""),
               {"potion_order_id": order_id})  


            result = connection.execute(sqlalchemy.text("""SELECT id
                                                        FROM DATE
                                                        ORDER BY id DESC
                                                        LIMIT 1"""))
            time_id = result.scalar()

            if potions_to_insert:
                insert_values = ", ".join(
                    [f"(:potion_order_id, :time_id, '{potion_type}', {quantity})" for potion_type, quantity in potions_to_insert]
                )

                connection.execute(sqlalchemy.text(f"""INSERT INTO potions 
                                                   (potion_order_id, time_id, potion_type, quantity) 
                                                   VALUES {insert_values}"""),
                                   {"potion_order_id": order_id, "time_id": time_id})
            
            #, num_red_potions, num_green_potions, num_blue_potions, num_dark_potions) 
            #, :num_red_potions, :num_green_potions, :num_blue_potions, :num_dark_potions
            # "num_red_potions": pot_r, "num_green_potions": pot_g, "num_blue_potions": pot_b, "num_dark_potions": pot_d
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
        potion_list = []
        green = [0,100,0,0]
        red = [100,0,0,0]
        blue = [0,0,100,0]
        dark = [0,0,0,100]

        #convert all into green pots
        while num_green_ml >= 100 and total_potion_amount < potion_capacity:
            num_green_ml -= 100
            total_potion_amount += 1
            add_or_increment_item(potion_list, {'potion_type': green, 'quantity': 1})
        while num_red_ml >= 100 and total_potion_amount < potion_capacity:
            num_red_ml -= 100
            total_potion_amount += 1
            add_or_increment_item(potion_list, {'potion_type': red, 'quantity': 1})
        while num_blue_ml >= 100 and total_potion_amount < potion_capacity:
            num_blue_ml -= 100
            total_potion_amount += 1
            add_or_increment_item(potion_list, {'potion_type': blue, 'quantity': 1})
        while num_dark_ml >= 100 and total_potion_amount < potion_capacity:
            num_dark_ml -= 100
            total_potion_amount += 1
            add_or_increment_item(potion_list, {'potion_type': dark, 'quantity': 1})

        return potion_list

if __name__ == "__main__":
    print(get_bottle_plan())