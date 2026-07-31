# Disclaimer

## 1. Purpose

This repository is a research project for **LLM persona template composition**.

The `attributes/` directory ships generic personality / speech / archetype / visual /
hobby attribute templates. These templates are designed to be combined (blended) at
runtime to construct LLM persona configurations.

## 2. Intended Use

The bundled templates are intended for:

- Research into modular LLM persona construction
- Experimentation with attribute blending
- Building production LLM systems with configurable personas

The bundled templates are **not** intended to reproduce, impersonate, or derive from
any specific copyrighted character, person, or creative work.

## 3. Licensing

- Code (the `hersona` package, CLI, scripts, schema): MIT
- Attribute templates (`attributes/**/*.yaml`): CC0 1.0 (public domain dedication)
- Documentation: CC-BY-4.0

Users of this repository are responsible for ensuring their own use complies with
applicable laws and the terms of any third-party services they integrate with.

## 4. LLM Output

Outputs produced by LLMs that consume the bundled templates are **not** the work of
this project and are not endorsed, approved, or licensed by this project. The
handling (publication, distribution, commercial use) of LLM outputs is the sole
responsibility of the user.

## 5. No Warranty

This repository is provided "as is", without warranty of any kind. The authors are
not liable for any damages arising from use of this repository.

## 6. AI disclosure and companion-chatbot regulation

hersona composes personas, and `persona_lock` is on by default, which instructs
the model to hold the persona against requests to drop it. If you deploy such a
persona in a user-facing product, **you** are responsible for any applicable
AI-disclosure duty — for example California SB 243 (effective 2026-01-01), the
chatbot statutes enacted in several other US states, and the EU AI Act's
transparency obligations (from 2026-08-02 for EU customers).

hersona provides an opt-in `--disclosure` directive that asks the persona to
answer honestly when asked whether it is an AI, overriding persona lock. That
directive is a prompt, not a guarantee: the model may ignore it, and it cannot
implement in-UI disclosure, minor-specific reminders, age assurance, crisis
referral, or record-keeping. Those remain entirely with the operator. See
[SECURITY.md](./SECURITY.md) for the breakdown.

## 7. Contact

To report an issue:
- GitHub: @shiro-0x
- X:https://x.com/hersona_agent 


---

Last updated: 2026-07-30
