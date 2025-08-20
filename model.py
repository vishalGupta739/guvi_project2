class HospitalBed:
    # Constructor to initialize the attributes
    def __init__(self, bed_id, status, location):
        self.bed_id = bed_id          # Bed ID as an integer
        self.status = status          # Bed status (e.g., 'Occupied', 'Available', 'Maintenance')
        self.location = location      # Bed location (e.g., 'Ward A, Room 101')

    # Method to update the status of the bed
    def update_status(self, new_status):
        """
        Updates the status of the hospital bed.
        """
        self.status = new_status
        print(f"Bed {self.bed_id} status updated to: {self.status}")

    # Method to display all bed information
    def display_info(self):
        """
        Displays all information about the hospital bed.
        """
        print("--- Hospital Bed Information ---")
        print(f"Bed ID: {self.bed_id}")
        print(f"Status: {self.status}")
        print(f"Location: {self.location}")
        print("-------------------------------")

# Example usage of the HospitalBed class
if __name__ == "__main__":
    # Create a new bed object
    bed1 = HospitalBed(bed_id=1, status="Available", location="Ward 3, Room 2B")

    # Display the initial information
    bed1.display_info()

    # Update the bed status
    bed1.update_status("Occupied")

    # Display the updated information
    bed1.display_info()