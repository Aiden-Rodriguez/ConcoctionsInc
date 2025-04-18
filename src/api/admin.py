from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(auth.get_api_key)],
)

@router.post("/reset")
def reset():
    """
    Reset the game state. Gold goes to 100, all potions are removed from
    inventory, and all barrels are removed from inventory. Carts are all reset.
    """
    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text("""UPDATE global_inventory 
                                           SET
                                           potion_capacity = 50, 
                                           ml_capacity = 10000,
                                           reset_timestamp = DEFAULT"""))
        
        connection.execute(sqlalchemy.text("""UPDATE potion_info_table
                                           SET
                                           "1g_strat" = False
                                           """))
        
    return "OK"

