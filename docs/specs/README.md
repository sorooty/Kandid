# Specs

One spec per feature, created with the `/feature` command. It fits on one page and is the reference for implementation and review.

## MVP ([ADR 0007](../adr/0007-mvp-scope.md), [ADR 0008](../adr/0008-restricted-scope.md))

| Spec | Feature | Status |
|---|---|---|
| [01](01-account.md) | Account | Validated |
| [02](02-profile-from-cv.md) | Profile from the CV | To validate |
| [03](03-offer-import.md) | Offer import | To validate |
| [04](04-tailored-letter.md) | Tailored letter and CV suggestions | To validate |
| [05](05-application-tracking.md) | Application tracking, spreadsheet view, export | To validate |
| [06](06-quick-add.md) | Quick add and import of an existing spreadsheet | To validate |
| [07](07-dashboard.md) | Dashboard | To validate |

## Implementation order

1. **01 Account**: everything else depends on it.
2. **05 Tracking** then **06 Quick add**: the tool is useful from this point, even without AI.
3. **07 Dashboard**: it builds on the tracking data.
4. **03 Offer import**, then **02 Profile**: first AI building blocks.
5. **04 Tailored letter**: it combines the profile and the offer.
