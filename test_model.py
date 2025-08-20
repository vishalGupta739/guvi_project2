# test_model.py
from model import HospitalBed

def test_hospital_bed():
    # Create a hospital bed instance
    bed = HospitalBed(bed_id=101, occupied=False, patient_name=None)
    
    # Test initial state
    assert bed.bed_id == 101
    assert bed.occupied == False
    assert bed.patient_name is None
    print("Initial state test passed.")
    
    # Test occupying the bed
    bed.occupy_bed("John Doe")
    assert bed.occupied == True
    assert bed.patient_name == "John Doe"
    print("Occupy bed test passed.")
    
    # Test vacating the bed
    bed.vacate_bed()
    assert bed.occupied == False
    assert bed.patient_name is None
    print("Vacate bed test passed.")

if __name__ == "__main__":
    test_hospital_bed()
    print("All tests passed successfully!")
    
    
    
