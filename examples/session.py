import datetime
import os

from aind_behavior_services.session import AindBehaviorSessionModel

session = AindBehaviorSessionModel(
    date=datetime.datetime.now(tz=datetime.timezone.utc),
    experiment="AindVrForaging",
    root_path="c://",
    subject="test",
    notes="test session",
    experiment_version="0.1.0",
    allow_dirty_repo=True,
    skip_hardware_validation=False,
    experimenter=["Foo", "Bar"],
)


def main(path_seed: str = "./local/{schema}.json"):
    os.makedirs(os.path.dirname(path_seed), exist_ok=True)
    models = [session]

    for model in models:
        with open(path_seed.format(schema=model.__class__.__name__), "w", encoding="utf-8") as f:
            f.write(model.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
