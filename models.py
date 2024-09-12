from dotenv import load_dotenv
load_dotenv()

import os
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy import Date, Text, Boolean, JSON, ARRAY
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class UserSchedule(Base):
    __tablename__ = 'user_schedules'
    id = Column(Integer, primary_key=True)
    discord_id = Column(String, unique=True, nullable=False)
    username = Column(String, nullable=False)
    # Schedule columns
    A1 = Column(String)
    B1 = Column(String)
    C1 = Column(String)
    D1 = Column(String)
    E1 = Column(String)
    A2 = Column(String)
    B2 = Column(String)
    C2 = Column(String)
    D2 = Column(String)
    E2 = Column(String)
    
class SchoolSchedule(Base):
    __tablename__ = 'school_schedules'

    id = Column(Integer, primary_key=True)
    schedule_date = Column(Date, nullable=False)
    uniform = Column(Text, nullable=False)
    school_open = Column(Boolean, nullable=False)
    courses = Column(JSON, nullable=True)  # Dictionary of course names and alternate rooms. Also implementation of AP Flex
    block_order = Column(ARRAY(Text), nullable=True)  # New column for block order (list of blocks, e.g., ['1A', '1B', '1C'])
    block_times = Column(ARRAY(Text), nullable=True)
    

# Connect to the Heroku PostgreSQL database
#DATABASE_URL = os.environ['postgresql://u5hsl3t8vpl42s:pe6a13af81a75d26bf7ec16ed5614d296602e45c12f84e7dc965e840334951295@cd1goc44htrmfn.cluster-czrs8kj4isg7.us-east-1.rds.amazonaws.com:5432/d66o2tq3s18vlt']
engine = create_engine('postgresql+psycopg2://u5hsl3t8vpl42s:pe6a13af81a75d26bf7ec16ed5614d296602e45c12f84e7dc965e840334951295@cd1goc44htrmfn.cluster-czrs8kj4isg7.us-east-1.rds.amazonaws.com:5432/d66o2tq3s18vlt')

# Create the tables in the database
Base.metadata.create_all(engine)