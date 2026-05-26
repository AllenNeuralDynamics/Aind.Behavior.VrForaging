# Curricula API

::: aind_behavior_vr_foraging_curricula

## Authoring Notes

To include module-specific narrative content in generated curriculum pages, add a `README.md` file inside each curriculum module directory:

`src/packages/aind_behavior_vr_foraging_curricula/src/aind_behavior_vr_foraging_curricula/<curriculum_name>/README.md`

During docs generation, the curricula builder discovers this file (when present) and renders its Markdown under a **Module README** section on that curriculum page.
Local relative asset references in that Markdown (for example, `assets/diagram.svg`) are not currently supported.
