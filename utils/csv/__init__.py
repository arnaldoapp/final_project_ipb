import csv

def initialize_csv(file_name, header=[]):
    """Initializes the CSV file by writing the header"""
    with open(file_name, mode='w', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow(header)

def write_agreement(file_name, data):
    """Writes the agreement details to the CSV file"""
    with open(file_name, mode='a', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)

        # Log the agreement tick
        csv_writer.writerow(data) 
