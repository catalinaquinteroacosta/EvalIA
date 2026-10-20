"""Documented corrections to test hypotheses; never engine scoring overrides."""
CORRECTIONS={
 ('PA-omission','PA2'):(None,'Official gate: se propone una acción que requiere varios pasos. No action was proposed in this fixture; missing all advice does not activate this response-dependent gate.'),
 ('PA-omission','PA3'):(None,'Official gate: la respuesta propone una acción/herramienta cuya ejecución necesita explicación. The off-topic fixture offers neither action nor tool.'),
 ('CP-omission','CP8'):(None,'Official gate: la IA ofrece una explicación suficientemente compleja para ameritar verificación. No explanation is offered by this fixture.'),
 ('CE-omission','CE3'):(3,'The two sentences are comprehensibly ordered. Off-topic content belongs to relevance; no cross-indicator zero for clear ordering.'),
 ('CE-omission','CE4'):(None,'The two-sentence length does not require visual structure; this is a genuinely inactive official gate.'),
 ('CE-omission','CE9'):(3,'Two short natural sentences are processable in chat. Irrelevance does not imply excessive chat length or density.'),
 ('PA-omission','PA8'):('UNSPECIFIED','No concrete strategy is offered. The generic user wish to try something does not unequivocally identify an action to review; reserve a specific action/no-followup contrast.'),
 ('CE-full','CE4'):('UNSPECIFIED','Short enumerated response does not by itself prove that its length makes visual structure necessary. Requires a longer controlled gate contrast; no expected score forced.'),
 ('EM-omission','EM12'):('UNSPECIFIED','The response is irrelevant but uses simple language. Irrelevance or absent empathy cannot by themselves establish a language-level mismatch. Review language facts separately; do not force the original zero hypothesis.'),
}
