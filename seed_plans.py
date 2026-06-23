"""Script to seed the database with Kairos subscription plans."""

from personalhq import create_app
from personalhq.extensions import db
from personalhq.models.plans import Plan

# Initialize the Flask application to access the database context
app = create_app()

def seed_plans():
    with app.app_context():
        # The finalized tiers from the landing page
        plans_data = [
            {"name": "Basic", "price": 0, "access_level": 1},
            {"name": "Pro", "price": 9, "access_level": 2},
            {"name": "Limitless", "price": 19, "access_level": 3},
            {"name": "Lifetime", "price": 299, "access_level": 4}
        ]

        print("Seeding plans...")
        
        for plan_info in plans_data:
            # Check if the plan already exists by name
            existing_plan = Plan.query.filter(Plan.name.ilike(plan_info["name"])).first()
            
            if not existing_plan:
                new_plan = Plan(
                    name=plan_info["name"],
                    price=plan_info["price"],
                    access_level=plan_info["access_level"]
                )
                db.session.add(new_plan)
                print(f"Created new plan: {plan_info['name']}")
            else:
                # Update existing plan details in case prices or levels changed
                existing_plan.price = plan_info["price"]
                existing_plan.access_level = plan_info["access_level"]
                print(f"Updated existing plan: {plan_info['name']}")

        # Commit all changes to the database
        db.session.commit()
        print("Successfully seeded all plans!")

if __name__ == "__main__":
    seed_plans()