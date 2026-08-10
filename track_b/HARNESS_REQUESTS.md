# Harness change requests from Track B

Track B does not edit src/. Changes that would help, for whoever owns the
harness next:

1. Salience heterogeneity in the task family. HardIntegrationTask gives every
   required container the same salience (0.9 via prompt naming), so the
   attention schema's within-tier ranking is tie-broken alphabetically and
   ANY attention_noise above zero fully shuffles it. Consequence: AST
   perturbation dose-responses are step-shaped (0 versus above-0) rather than
   graded. A task variant where required containers carry distinct salience
   levels (for example, staggered prompt emphasis) would make noise
   dose-responses graded and the covariance detector correspondingly more
   informative. See PREREG.md, limitations.

2. Whitespace tokenizer, already on the FINDINGS open list: capacity numbers
   quoted in tokens assume 5-token containers; a real tokenizer changes the
   delivered-count mapping and PREREG.md's capacity settings would need
   re-deriving.
