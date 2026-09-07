# Catch wrong assumptions before building

- Wrong account or region: stop and return to the assigned sandbox. Check STS
  identity and the Console region before creating resources.
- CIDRs already in use: choose unused, nonoverlapping ranges and update every
  subnet and route consistently in your worksheet.
- Missing permission: record the denied AWS action and ask the account owner for
  the required lab access. Do not borrow another account's credentials.
- Different customer Hydra version: record the difference. Keep this pinned
  practice baseline separate from a customer-version compatibility claim.

**Gate:** identify the assumption, correct the worksheet and recheck it. An
instructor's successful run does not prove your own environment is ready.
