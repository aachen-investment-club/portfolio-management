import csv


def query_to_csv(session, query, output_filename: str):
    result = session.execute(query)
    fieldnames = list(result.keys())

    with open(output_filename, mode='w', newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()

        for row in result:
            writer.writerow(row._asdict())
        
    print(f"Successfully written query results to {output_filename}")