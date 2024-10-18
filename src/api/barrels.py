from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db

#As a very basic initial logic, purchase a new small green potion barrel only if the number of potions 
#in inventory is less than 10. Always mix all available green ml if any exists. Offer up for sale in 
#the catalog only the amount of green potions that actually exist currently in inventory.

router = APIRouter(
    prefix="/barrels",
    tags=["barrels"],
    dependencies=[Depends(auth.get_api_key)],
)

class Barrel(BaseModel):
    sku: str

    ml_per_barrel: int
    potion_type: list[int]
    price: int

    quantity: int

@router.post("/deliver/{order_id}")
def post_deliver_barrels(barrels_delivered: list[Barrel], order_id: int):
    # interact with db

    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("""SELECT EXISTS
                                                    (SELECT 1 FROM barrel_order_table 
                                                    WHERE barrel_order_id = :barrel_order_id)"""), 
                                    {"barrel_order_id": order_id})
        #if the row exists, this transaction has already happened!! bad!
        row = result.scalar()
        if row == True:
            return "OK"
        else: # if no exist then go ahead and change the db!

            result = connection.execute(sqlalchemy.text("""SELECT num_green_ml, num_red_ml, num_dark_ml, num_blue_ml, gold 
                                                        FROM global_inventory"""))
            row = result.mappings().one()  # Using mappings to access the columns by name

            # Extract values from the row
        
            num_green_ml = row['num_green_ml']
            num_red_ml = row['num_red_ml']
            num_blue_ml = row['num_blue_ml']
            num_dark_ml = row['num_dark_ml']
        
            gold = row['gold']
            gold_paying = 0
            barrels_to_insert = []

            for barrel in barrels_delivered :
                gold -= barrel.price * barrel.quantity
                gold_paying += barrel.price * barrel.quantity
                if barrel.potion_type == [1,0,0,0]:
                    num_red_ml += barrel.ml_per_barrel * barrel.quantity
                    barrels_to_insert.append(([1,0,0,0], barrel.ml_per_barrel * barrel.quantity))  
                if barrel.potion_type == [0,1,0,0]:
                    num_green_ml += barrel.ml_per_barrel * barrel.quantity
                    barrels_to_insert.append(([0,1,0,0], barrel.ml_per_barrel * barrel.quantity)) 
                if barrel.potion_type == [0,0,1,0]:
                    num_blue_ml += barrel.ml_per_barrel * barrel.quantity
                    barrels_to_insert.append(([0,0,1,0], barrel.ml_per_barrel * barrel.quantity)) 
                if barrel.potion_type == [0,0,0,1]:
                    num_dark_ml += barrel.ml_per_barrel * barrel.quantity
                    barrels_to_insert.append(([0,0,0,1], barrel.ml_per_barrel * barrel.quantity)) 


            connection.execute(sqlalchemy.text("""INSERT INTO barrel_order_table 
                                               (barrel_order_id, gold_cost) 
                                               VALUES 
                                               (:barrel_order_id, :gold_paying)"""),
                               {"barrel_order_id": order_id, "gold_paying": gold_paying})  

            result = connection.execute(sqlalchemy.text("""SELECT id
                                                        FROM DATE
                                                        ORDER BY id DESC
                                                        LIMIT 1"""))
            time_id = result.scalar()

        if barrels_to_insert:
            insert_values = ", ".join(
                [f"(:barrel_order_id, :time_id, '{barrel_type}', {quantity_ml})" for barrel_type, quantity_ml in barrels_to_insert]
            )

            connection.execute(sqlalchemy.text(f"""INSERT INTO barrels 
                                               (barrel_order_id, time_id, barrel_type, quantity_ml) 
                                               VALUES {insert_values}"""),
                               {"barrel_order_id": order_id, "time_id": time_id})

    
            connection.execute(sqlalchemy.text("""UPDATE global_inventory 
                                               SET num_green_ml = :num_green_ml, num_red_ml = :num_red_ml, num_blue_ml = :num_blue_ml, num_dark_ml = :num_dark_ml, gold = :gold;"""),
                                {"num_green_ml": num_green_ml, "num_red_ml": num_red_ml, "num_blue_ml": num_blue_ml,"num_dark_ml": num_dark_ml, "gold": gold})
        
            print(f"barrels delievered: {barrels_delivered} order_id: {order_id}")
            return "OK"

#deal with adding dictionary stuff
def add_or_increment_item(item_list, new_item):
    for item in item_list:
        #check if the item with the same sku already exists
        if item['sku'] == new_item['sku']:
            #increment the quantity by the value of the new item
            item['quantity'] += new_item['quantity']
            return

    #if the item does not exist, add it to the list
    item_list.append(new_item)

# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):

    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("""SELECT num_green_ml, num_blue_ml, num_red_ml, num_dark_ml, gold, ml_capacity 
                                                    FROM global_inventory"""))

        row = result.mappings().one()
        num_green_ml = row['num_green_ml']
        num_blue_ml = row['num_blue_ml']
        num_red_ml = row['num_red_ml']
        num_dark_ml = row['num_dark_ml']
        ml_total = num_dark_ml + num_blue_ml + num_green_ml + num_red_ml
        ml_capacity = row['ml_capacity']
        gold = row['gold']

        result = connection.execute(sqlalchemy.text("""SELECT day
                                                        FROM DATE
                                                        ORDER BY id DESC
                                                        LIMIT 1"""))
        #whatever the day is
        day = result.scalar()


        #possibly reimpliment later w/ potion proportions
        # result = connection.execute(sqlalchemy.text("""
        #     SELECT potion_sku, SUM(inventory) AS inventory_count
        #     FROM potion_info_table
        #     WHERE potion_sku IN ('red', 'green', 'blue', 'dark')
        #     GROUP BY potion_sku"""))
        # rows = result.fetchall()

        # num_green_potions = 0
        # num_blue_potions = 0
        # num_red_potions = 0
        # num_dark_potions = 0

        # for row in rows:
        #     potion_sku = row[0]
        #     inventory_count = row[1]
    
        #     #update later to be based on ml total of potions or something
        #     if potion_sku == 'green':
        #         num_green_potions = inventory_count
        #     elif potion_sku == 'blue':
        #         num_blue_potions = inventory_count
        #     elif potion_sku == 'red':
        #         num_red_potions = inventory_count
        #     elif potion_sku == 'dark':
        #         num_dark_potions = inventory_count




        # change later to accomidate buyign bigger barrels too
        buying_list = []
        ml_compare_list = [num_red_ml, num_green_ml, num_blue_ml, num_dark_ml]
        #potion_compare_list = [num_red_potions, num_green_potions, num_blue_potions, num_dark_potions]


        loop_counter = 0
        max_iterations = 1000

        while ml_total <= ml_capacity and gold > 0:
            loop_counter += 1
            if loop_counter > max_iterations:
                #looped too much prob bugged
                return "Not Sigma loop"
            
            #get index of lowest ml count / pots   
            #min_value_ml = min(ml_compare_list)
            #min_indexes_ml = [i for i, num in enumerate(ml_compare_list) if num == min_value_ml]

            #min_value_potion = min(potion_compare_list)
            #min_indexes_potion = [i for i, num in enumerate(potion_compare_list) if num == min_value_potion]

            purchased_any = False

            for barrel in wholesale_catalog:
                    
                #handle buying based on lowest potion count currently.
                #dont buy mini barrels frick mini barrels
                #red
                if barrel.potion_type == [1,0,0,0] and "MINI" not in barrel.sku and day != "Edgeday":
                    while barrel.quantity > 0 and barrel.ml_per_barrel + ml_total <= ml_capacity and gold >= barrel.price and num_red_ml < 1000:
                        sku = barrel.sku
                        barrel.quantity -= 1
                        gold -= barrel.price
                        ml_total += barrel.ml_per_barrel
                        num_red_ml += barrel.ml_per_barrel
                        add_or_increment_item(buying_list, {'sku': sku, 'quantity': 1})
                        purchased_any = True
                #green
                elif barrel.potion_type == [0,1,0,0] and "MINI" not in barrel.sku and day != "Bloomday":
                    while barrel.quantity > 0 and barrel.ml_per_barrel + ml_total <= ml_capacity and gold >= barrel.price and num_green_ml < 1000:
                        sku = barrel.sku
                        barrel.quantity -= 1
                        gold -= barrel.price
                        ml_total += barrel.ml_per_barrel
                        num_green_ml += barrel.ml_per_barrel
                        add_or_increment_item(buying_list, {'sku': sku, 'quantity': 1})
                        purchased_any = True
                #blue
                elif barrel.potion_type == [0,0,1,0] and "MINI" not in barrel.sku and day != "Arcanaday":
                    while barrel.quantity > 0 and barrel.ml_per_barrel + ml_total <= ml_capacity and gold >= barrel.price and num_blue_ml < 1000:
                        sku = barrel.sku
                        barrel.quantity -= 1
                        gold -= barrel.price
                        ml_total += barrel.ml_per_barrel
                        num_blue_ml += barrel.ml_per_barrel
                        add_or_increment_item(buying_list, {'sku': sku, 'quantity': 1})
                        purchased_any = True
                #dark
                elif barrel.potion_type == [0,0,0,1] and "MINI" not in barrel.sku:
                    while barrel.quantity > 0 and barrel.ml_per_barrel + ml_total <= ml_capacity and gold >= barrel.price and num_dark_ml < 1000:
                        sku = barrel.sku
                        barrel.quantity -= 1
                        gold -= barrel.price
                        ml_total += barrel.ml_per_barrel
                        num_dark_ml += barrel.ml_per_barrel
                        add_or_increment_item(buying_list, {'sku': sku, 'quantity': 1})
                        purchased_any = True

            if purchased_any == False:
                break

        return buying_list