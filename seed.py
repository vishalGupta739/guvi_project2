import csv
from datetime import datetime
from pathlib import Path

from app import db, Hospital, app

CSV_BEDS = Path('BedsView.csv')
CSV_ALERTS = Path('Alerts.csv')

# BedsView.csv columns:
# Hospital Name,City,Region,Total Beds,Occupied Beds,Available Beds,Occupancy Rate (%)
# Alerts.csv columns:
# Hospital Name,City,Region,Available Beds,Occupancy Rate (%)

def parse_int(value, default=0):
	try:
		return int(str(value).strip())
	except Exception:
		return default


def seed_from_beds():
	if not CSV_BEDS.exists():
		print('BedsView.csv not found, skipping')
		return 0, 0
	created = 0
	updated = 0
	with app.app_context():
		with CSV_BEDS.open(newline='', encoding='utf-8') as f:
			reader = csv.DictReader(f)
			for row in reader:
				name = (row.get('Hospital Name') or '').strip()
				region = (row.get('Region') or '').strip()
				total_beds = parse_int(row.get('Total Beds'), 0)
				available_beds = parse_int(row.get('Available Beds'), 0)
				if not name or not region:
					continue
				existing = Hospital.query.filter_by(name=name, region=region).first()
				if existing is None:
					db.session.add(Hospital(
						name=name,
						region=region,
						total_beds=total_beds,
						available_beds=available_beds,
						last_updated=datetime.utcnow(),
					))
					created += 1
				else:
					existing.total_beds = total_beds
					existing.available_beds = available_beds
					existing.last_updated = datetime.utcnow()
					updated += 1
		db.session.commit()
	return created, updated


def update_from_alerts():
	if not CSV_ALERTS.exists():
		print('Alerts.csv not found, skipping')
		return 0
	updates = 0
	with app.app_context():
		with CSV_ALERTS.open(newline='', encoding='utf-8') as f:
			reader = csv.DictReader(f)
			for row in reader:
				name = (row.get('Hospital Name') or '').strip()
				region = (row.get('Region') or '').strip()
				available_beds = parse_int(row.get('Available Beds'), 0)
				if not name or not region:
					continue
				existing = Hospital.query.filter_by(name=name, region=region).first()
				if existing is None:
					# If it does not exist yet, create a minimal record
					db.session.add(Hospital(
						name=name,
						region=region,
						total_beds=max(available_beds, 0),
						available_beds=available_beds,
						last_updated=datetime.utcnow(),
					))
				else:
					existing.available_beds = available_beds
					existing.last_updated = datetime.utcnow()
				updates += 1
		db.session.commit()
	return updates


if __name__ == '__main__':
	c, u = seed_from_beds()
	print(f'Seed from BedsView.csv -> created={c}, updated={u}')
	al = update_from_alerts()
	print(f'Updated from Alerts.csv -> updates={al}')
