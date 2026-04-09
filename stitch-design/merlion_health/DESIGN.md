# Design System Specification: Clinical Serenity

## 1. Overview & Creative North Star
**North Star: The Empathetic Architect**
In the Singaporean healthcare context, "trust" is not merely the absence of error; it is the presence of quiet, organized authority. This design system moves away from the "cluttered clinical" aesthetic to embrace **The Empathetic Architect**—a philosophy that balances high-fidelity precision with a human-centric softness. 

The system breaks the "template" look by utilizing **intentional asymmetry** and **tonal layering**. Rather than rigid grids, we use breathing room (whitespace) and sophisticated font scaling to guide the eye. It is designed to feel as reliable as a specialist's consultation, yet as fluid as a modern messaging interface.

---

## 2. Colors: The Tonal Depth Strategy
We move beyond flat UI by using a palette that mimics the natural behavior of light and sterile, high-end materials.

### Palette Highlights
- **Primary (`#006565`):** Medical Teal. Used for primary actions and brand presence.
- **Secondary (`#206393`):** Soft Blue. Used for secondary navigation and informative accents.
- **Surface (`#f7fafc`):** A cool-tinted white that reduces eye strain compared to pure `#ffffff`.

### The "No-Line" Rule
**Strict Mandate:** Designers are prohibited from using 1px solid borders to section content. Layout boundaries must be defined solely through background color shifts.
*   *Example:* A `surface-container-low` section sitting on a `surface` background provides enough contrast to denote a new area without the "boxed-in" feel of a stroke.

### Glass & Gradient Rule
To achieve a premium "High-Fidelity" feel:
- **CTAs:** Use a subtle linear gradient from `primary` (`#006565`) to `primary_container` (`#008080`) at a 135-degree angle. This adds "soul" and dimension.
- **Floating Modals:** Utilize **Glassmorphism**. Set surface colors to 80% opacity with a `20px` backdrop-blur. This ensures the clinical portal feels modern and integrated, not "pasted on."

---

## 3. Typography: Editorial Authority
We pair **Manrope** (Display/Headlines) with **Inter** (Body/UI) to create a sophisticated hierarchy that feels both modern and legible.

| Role | Token | Font | Size | Intent |
| :--- | :--- | :--- | :--- | :--- |
| **Display** | `display-lg` | Manrope | 3.5rem | Bold, welcoming hero statements. |
| **Headline** | `headline-md` | Manrope | 1.75rem | Clear section headers in the clinical portal. |
| **Title** | `title-md` | Inter | 1.125rem | Critical info (e.g., Patient Name). |
| **Body** | `body-md` | Inter | 0.875rem | Messaging and medical records. |
| **Label** | `label-sm` | Inter | 0.6875rem | Metadata and status timestamps. |

**The Hierarchy Rule:** Headlines should use a tighter letter-spacing (-0.02em) to feel "editorial," while Body text remains at default tracking for maximum legibility in high-stress medical contexts.

---

## 4. Elevation & Depth: Tonal Layering
Traditional shadows are often too heavy for healthcare. We use **Tonal Layering** to create hierarchy.

- **The Layering Principle:** Stack `surface-container` tiers. 
    *   Base: `surface` (`#f7fafc`)
    *   Section: `surface-container-low` (`#f1f4f6`)
    *   Interactive Card: `surface-container-lowest` (`#ffffff`)
- **Ambient Shadows:** For floating elements, use a shadow with a 24px blur, 4% opacity, tinted with `on-surface` (`#181c1e`). Avoid grey; use the natural tint of the background.
- **The "Ghost Border" Fallback:** If a divider is vital for accessibility, use `outline_variant` (`#bdc9c8`) at **15% opacity**. It should be felt, not seen.

---

## 5. Components: Precision & Accessibility

### Buttons & Chips
- **Primary Button:** High-pill shape (`rounded-full`). Gradient fill (`primary` to `primary_container`). White text (`on_primary`).
- **Status Chips:** 
    *   *On-Track:* `tertiary_container` (`#338236`) background with `on_tertiary_container` text.
    *   *Non-Adherence:* `error_container` (`#ffdad6`) background with `on_error_container` text.
- **Note:** Chips should never have borders; use the container color for containment.

### Input Fields
- **State:** Use `surface_container_highest` (`#e0e3e5`) for the input background. 
- **Focus:** Instead of a thick border, use a 2px glow of `primary_fixed` (`#93f2f2`).
- **Error:** Text turns to `error` (`#ba1a1a`) with a soft `error_container` highlight behind the field.

### Messaging Bubbles (Mobile Context)
- **Patient:** `secondary_container` (`#90c9ff`) with `on_secondary_container` text.
- **Clinician:** `surface_container_highest` (`#e0e3e5`) with `on_surface` text.
- **Shape:** Use `rounded-xl` for the bubble, but `rounded-sm` on the corner pointing to the speaker for "tail-less" directionality.

### Clinical Cards
- **Forbid Dividers:** Use vertical white space (Token `6` or `8`) to separate patient vitals. 
- **Nesting:** Patient data sits on a `surface-container-lowest` card to "pop" against the `surface-container-low` portal background.

---

## 6. Do’s and Don’ts

### Do
- **Do** use `manrope` for numbers in clinical charts; its geometric nature makes data feel precise.
- **Do** leave significant padding (Spacing `12` or `16`) around critical medical alerts to prevent "information crowding."
- **Do** use `primary_fixed_dim` for "read-only" data points to maintain brand color without suggesting interactivity.

### Don’t
- **Don’t** use pure black (`#000000`) for text. Always use `on_surface` (`#181c1e`) to keep the interface soft.
- **Don’t** use sharp corners. Every element must have at least `rounded-md` (0.75rem) to maintain the "Empathetic" feel.
- **Don’t** use high-saturation red for errors. Use the `error` (`#ba1a1a`) token—it is authoritative but doesn't induce panic.