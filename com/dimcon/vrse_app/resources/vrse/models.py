from sqlalchemy import Column, String, Boolean, DateTime, JSON, create_engine
from com.dimcon.vrse_app.resources.base import Base
import datetime

class Passkit_Member(Base):
    __tablename__ = 'members'
    
    id = Column(String, primary_key=True)
    tier_id = Column(String, nullable=False)
    program_id = Column(String, nullable=False)
    person = Column(JSON, nullable=False)
    meta_data = Column(JSON)
    opt_out = Column(Boolean, nullable=False, default=False)
    expiry_date = Column(DateTime)
    pass_overrides = Column(JSON)
    pass_meta_data = Column(JSON)
    created = Column(DateTime, default=datetime.datetime.utcnow)
    
    def __repr__(self):
        return f"<Member(id={self.id}, program_id={self.program_id})>"

if __name__ == "__main__":
    # Replace with your actual database connection string as needed
    engine = create_engine("sqlite:///members.db", echo=True)
    Base.metadata.create_all(engine)
    print("✅ Tables created successfully.")