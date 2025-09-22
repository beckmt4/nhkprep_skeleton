from typing import List, Dict
import sacrebleu

def compute_metrics(system: List[str], reference: List[str]) -> Dict[str, float]:
    # Simple line-by-line; real implementation should join or segment consistently
    sys_join = "\n".join(system)
    ref_join = "\n".join(reference)
    bleu = sacrebleu.corpus_bleu([sys_join], [[ref_join]]).score
    chrf = sacrebleu.corpus_chrf([sys_join], [[ref_join]]).score
    # TER not in sacrebleu by default; placeholder
    ter = 0.0
    return {"BLEU": bleu, "chrF": chrf, "TER": ter}
