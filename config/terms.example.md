# Job-title match terms : EDIT THIS (the /setup skill helps you build it)

A posting is kept only if its TITLE matches one of these, or a clearly similar
variant (case-insensitive). "Sr" == "Senior", "PM" == "Product Manager", etc.
One term per line. Lines starting with # are ignored.

The goal: specific enough to filter noise, broad enough not to miss good roles.
Aim for the real titles you would actually take, plus their obvious variants.

## Example (a product-manager search). Replace with yours.
Product Manager
Senior Product Manager
Staff Product Manager
Principal Product Manager
Group Product Manager
Lead Product Manager
Director of Product
Director of Product Management
Head of Product

## Exclusions (drop these even if a term above is a substring)
# Product Marketing Manager
# Associate Product Manager

## Hard filters (enforced in scripts/poll.py and the generation prompts)
# Uncomment / edit the ones you want. Leave commented to disable.
# - International location with no US option -> excluded
# - Requires 10+ years of experience in <your field> -> excluded
# - Salary stated AND top of range < 150000 -> excluded (no salary stated -> kept)
# - Company "ExampleCorp" UNLESS location is Remote or <your city> -> excluded
