from beanie import Document, Indexed


class Preference(Document):
    # ponytail: just user_id for now. Phase 8 adds task_type_routing,
    # later phases add digest settings etc. — don't guess those fields yet.
    user_id: Indexed(str, unique=True)

    class Settings:
        name = "preferences"
