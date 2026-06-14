from etl.extract import extract
from etl.transform import transform

from etl.logging_utils import write_log 

def main():

    write_log(
        "ETL pipeline started."
    )

    try:

        ...
        extract()
        transform()
        build_dimensions()
        build_facts()
        load()

        write_log(
            "ETL pipeline completed successfully."
        )

    except Exception as e:

        write_log(
            f"ETL pipeline failed: {e}"
        )

        raise