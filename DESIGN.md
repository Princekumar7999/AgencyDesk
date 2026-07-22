# AgencyDesk Design

Tenant isolation is enforced by pairing the JWT identity with an active agency context. Every tenant-scoped request must include `X-Agency-ID`, and `get_current_membership` verifies that the authenticated user has a membership in that agency before any data is returned. On top of that, every read and write query filters by `agency_id`, so a guessed UUID from another tenant resolves to nothing instead of leaking data.

Client visibility is handled at the query layer, not in the UI. Client users only see `is_client_visible = true` tasks, comments, and files, and they never get detailed time-entry rows. That means the backend enforces what the frontend can render, which prevents accidental leaks even if a route is called directly.

The identity model is one global `users` table plus per-agency `agency_memberships`. That lets one person belong to two agencies with different roles, such as client in one workspace and staff in another. The frontend keeps an active workspace selector and sends the chosen agency in the request headers, so the same login can safely switch roles without creating duplicate accounts.

One edge case handled well is invite and membership races. Pending invitations are upserted per agency/email, and invite acceptance is checked transactionally so a second acceptance fails cleanly instead of creating duplicate memberships. That same pattern is used to keep removals and reassignment safe when a member is deleted mid-project.