from datetime import datetime
from flask import Flask, jsonify, request, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///hospital.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


class Hospital(db.Model):
    __tablename__ = "hospitals"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, index=True)
    region = db.Column(db.String(120), nullable=False, index=True)
    total_beds = db.Column(db.Integer, nullable=False, default=0)
    available_beds = db.Column(db.Integer, nullable=False, default=0)
    last_updated = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "region": self.region,
            "total_beds": self.total_beds,
            "available_beds": self.available_beds,
            "last_updated": self.last_updated.isoformat() + "Z",
            "status": "CRITICAL" if self.available_beds <= 0 else "OK",
            "occupancy_rate": (0 if self.total_beds == 0 else round((self.total_beds - self.available_beds) / self.total_beds, 3)),
        }


with app.app_context():
    db.create_all()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/hospitals", methods=["GET"])  # list with filters
def list_hospitals():
    query = Hospital.query

    region = request.args.get("region")
    if region and region.lower() != "all":
        query = query.filter(Hospital.region == region)

    search = request.args.get("q")
    if search:
        like = f"%{search.strip()}%"
        query = query.filter(Hospital.name.ilike(like))

    min_available = request.args.get("min_available")
    if min_available is not None and min_available != "":
        try:
            min_val = int(min_available)
            query = query.filter(Hospital.available_beds >= min_val)
        except ValueError:
            pass

    sort = request.args.get("sort", "name")
    if sort == "available_desc":
        query = query.order_by(Hospital.available_beds.desc())
    elif sort == "available_asc":
        query = query.order_by(Hospital.available_beds.asc())
    elif sort == "updated_desc":
        query = query.order_by(Hospital.last_updated.desc())
    else:
        query = query.order_by(Hospital.name.asc())

    hospitals = [h.to_dict() for h in query.all()]
    return jsonify({"items": hospitals, "count": len(hospitals)})


@app.route("/api/hospitals", methods=["POST"])  # create
def create_hospital():
    data = request.get_json(silent=True) or {}

    name = (data.get("name") or "").strip()
    region = (data.get("region") or "").strip()
    total_beds = data.get("total_beds", 0)
    available_beds = data.get("available_beds", 0)

    error = _validate_beds_payload(name=name, region=region, total_beds=total_beds, available_beds=available_beds)
    if error:
        return jsonify({"error": error}), 400

    hospital = Hospital(
        name=name,
        region=region,
        total_beds=total_beds,
        available_beds=available_beds,
        last_updated=datetime.utcnow(),
    )
    db.session.add(hospital)
    db.session.commit()

    return jsonify(hospital.to_dict()), 201


@app.route("/api/hospitals/bulk", methods=["POST"])  # bulk upsert by (name, region)
def bulk_upsert_hospitals():
    payload = request.get_json(silent=True)
    if not isinstance(payload, list):
        return jsonify({"error": "Expected a JSON array of hospitals"}), 400

    created = 0
    updated = 0
    errors = []
    now = datetime.utcnow()

    for idx, item in enumerate(payload):
        if not isinstance(item, dict):
            errors.append({"index": idx, "error": "Item is not an object"})
            continue
        name = (item.get("name") or "").strip()
        region = (item.get("region") or "").strip()
        total_beds = item.get("total_beds", 0)
        available_beds = item.get("available_beds", 0)

        err = _validate_beds_payload(name=name, region=region, total_beds=total_beds, available_beds=available_beds)
        if err:
            errors.append({"index": idx, "error": err})
            continue

        existing = Hospital.query.filter_by(name=name, region=region).first()
        if existing is None:
            db.session.add(Hospital(
                name=name,
                region=region,
                total_beds=int(total_beds),
                available_beds=int(available_beds),
                last_updated=now,
            ))
            created += 1
        else:
            existing.total_beds = int(total_beds)
            existing.available_beds = int(available_beds)
            existing.last_updated = now
            updated += 1

    db.session.commit()
    return jsonify({"created": created, "updated": updated, "errors": errors}), 200


@app.route("/api/hospitals/<int:hospital_id>", methods=["PUT"])  # update
def update_hospital(hospital_id: int):
    hospital = Hospital.query.get_or_404(hospital_id)
    data = request.get_json(silent=True) or {}

    name = (data.get("name", hospital.name) or "").strip()
    region = (data.get("region", hospital.region) or "").strip()
    total_beds = data.get("total_beds", hospital.total_beds)
    available_beds = data.get("available_beds", hospital.available_beds)

    error = _validate_beds_payload(name=name, region=region, total_beds=total_beds, available_beds=available_beds)
    if error:
        return jsonify({"error": error}), 400

    hospital.name = name
    hospital.region = region
    hospital.total_beds = int(total_beds)
    hospital.available_beds = int(available_beds)
    hospital.last_updated = datetime.utcnow()

    db.session.commit()
    return jsonify(hospital.to_dict())


@app.route("/api/hospitals/<int:hospital_id>", methods=["GET"])  # get
def get_hospital(hospital_id: int):
    hospital = Hospital.query.get_or_404(hospital_id)
    return jsonify(hospital.to_dict())


@app.route("/api/regions", methods=["GET"])  # unique list of regions
def get_regions():
    rows = db.session.query(Hospital.region).distinct().order_by(Hospital.region.asc()).all()
    regions = [r[0] for r in rows]
    return jsonify({"regions": regions})


@app.route("/api/alerts", methods=["GET"])  # CRITICAL hospitals (<= threshold)
def get_alerts():
    threshold_raw = request.args.get("threshold", "0")
    try:
        threshold = int(threshold_raw)
    except Exception:
        threshold = 0
    rows = Hospital.query.filter(Hospital.available_beds <= threshold).order_by(Hospital.name.asc()).all()
    return jsonify({"items": [h.to_dict() for h in rows], "count": len(rows), "threshold": threshold})


@app.route("/api/stats", methods=["GET"])  # aggregate stats
def get_stats():
    query = Hospital.query
    region = request.args.get("region")
    if region and region.lower() != "all":
        query = query.filter(Hospital.region == region)

    hospitals = query.all()
    total_beds = sum(h.total_beds for h in hospitals)
    available_beds = sum(h.available_beds for h in hospitals)
    occupied_beds = max(total_beds - available_beds, 0)

    return jsonify({
        "total_beds": total_beds,
        "available_beds": available_beds,
        "occupied_beds": occupied_beds,
        "occupancy_rate": (0 if total_beds == 0 else round(occupied_beds / total_beds, 3)),
        "hospitals": len(hospitals),
    })


def _validate_beds_payload(name: str, region: str, total_beds, available_beds):
    if not name:
        return "'name' is required"
    if not region:
        return "'region' is required"
    try:
        total = int(total_beds)
        available = int(available_beds)
    except Exception:
        return "'total_beds' and 'available_beds' must be integers"

    if total < 0 or available < 0:
        return "Bed counts cannot be negative"
    if available > total:
        return "'available_beds' cannot exceed 'total_beds'"
    return None


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
