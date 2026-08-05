# Import formats

## Official ShootATA import
Accepts CSV, XLSX, HTML, or PDF tables. Recommended headings: `ata_number`, `name`, `state`, `category`, discipline target/hit fields, Minnesota target fields, `mn_clubs`, and `haa`. Average columns can substitute for hit columns.

## ShootScoreBoard report import
Accepts wide rows (`singles_hits`, `singles_targets`, etc.) or long rows (`discipline`, `hits`, `targets`). Name reconciliation first uses ATA number, then aliases, then fuzzy name matching.
