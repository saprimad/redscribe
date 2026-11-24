"""Local publication exports; no participant text or audio paths."""
from pathlib import Path
from .benchmark_matrix_reporting import build_matrix_reports

def export_publication(directory,state):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    from openpyxl.utils import get_column_letter
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    directory=Path(directory)
    summary,rows,efficiency=build_matrix_reports(state)
    wb=Workbook()
    wb.remove(wb.active)
    for name,data in (("Model summary",summary),("Recording results",rows),("Efficiency",efficiency)):
        ws=wb.create_sheet(name)
        if not data:
            continue
        fields=list(data[0])
        ws.append(fields)
        for row in data:
            ws.append([row.get(k) for k in fields])
        for cell in ws[1]:
            cell.font=Font(bold=True,color="FFFFFF")
            cell.fill=PatternFill("solid",fgColor="243B53")
        for i,k in enumerate(fields,1):
            ws.column_dimensions[get_column_letter(i)].width=min(38,max(15,len(k)+2))
            if k in ("wer","cer","corpus_wer","corpus_cer","macro_wer","macro_cer"):
                for cells in ws.iter_rows(min_row=2,min_col=i,max_col=i):
                    cells[0].number_format="0.00%"
        ws.freeze_panes="C2"
        ws.auto_filter.ref=ws.dimensions
    wb.save(directory/"scientific_results.xlsx")
    common=[r for r in summary if r["cohort"]=="common_completed" and r["corpus_wer"] is not None and r["corpus_cer"] is not None]
    def figure(name,draw):
        fig=Figure(figsize=(8,4.8),layout="constrained")
        FigureCanvasAgg(fig)
        ax=fig.add_subplot(111)
        draw(ax)
        for ext in ("svg","png"):
            fig.savefig(directory/(name+"."+ext),dpi=600)
    def accuracy(ax):
        x=list(range(len(common)))
        ax.bar([i-.19 for i in x],[100*r["corpus_wer"] for r in common],.38,label="WER")
        ax.bar([i+.19 for i in x],[100*r["corpus_cer"] for r in common],.38,label="CER")
        ax.set_xticks(x,[r["model_key"] for r in common],rotation=30,ha="right")
        ax.set_ylabel("Error rate (%)")
        ax.legend()
    def distribution(ax,metric="wer"):
        labels=[r["model_key"] for r in common]
        pids={p for p in state["identity"]["recordings"] if all(any(r["participant_id"]==p and r["model_key"]==m and r["status"]=="completed" and r["wer"] is not None and r["cer"] is not None for r in rows) for m in state["identity"]["models"])}
        ax.boxplot([[100*r[metric] for r in rows if r["model_key"]==m and r["participant_id"] in pids] for m in labels],tick_labels=labels)
        ax.tick_params(axis="x",labelrotation=30)
        ax.set_ylabel("Recording "+metric.upper()+" (%)")
    def heatmap(ax):
        import numpy as np
        models=state["identity"]["models"]
        ids=state["identity"]["recordings"]
        lookup={(r["model_key"],r["participant_id"]):r["wer"] for r in rows}
        values=np.array([[100*lookup[m,p] if lookup[m,p] is not None else np.nan for m in models] for p in ids])
        im=ax.imshow(np.ma.masked_invalid(values),aspect="auto",cmap="viridis")
        ax.set_xticks(range(len(models)),models,rotation=30,ha="right")
        ax.set_yticks(range(len(ids)),ids,fontsize=7)
        ax.figure.colorbar(im,ax=ax,label="WER (%)")
    def speed(ax):
        for r in common:
            subset=[x for x in rows if x["model_key"]==r["model_key"] and x["participant_id"] in common_ids and x["rtf"] is not None]
            if len(subset)!=len(common_ids) or not subset:
                continue
            x=sum(t["inference_seconds"] for t in subset)/sum(t["audio_seconds"] for t in subset)
            y=100*r["corpus_wer"]
            ax.scatter(x,y)
            ax.annotate(r["model_key"],(x,y),fontsize=8)
        ax.set_xlabel("Aggregate real-time factor")
        ax.set_ylabel("Corpus WER (%)")
    common_ids={pid for pid in state["identity"]["recordings"] if all(any(r["participant_id"]==pid and r["model_key"]==m and r["wer"] is not None and r["cer"] is not None for r in rows) for m in state["identity"]["models"])}
    if any(r["wer"] is not None for r in rows):
        figure("participant_wer_heatmap",heatmap)
    else:
        for ext in ("svg","png"):
            (directory/("participant_wer_heatmap."+ext)).unlink(missing_ok=True)
    if common:
        figure("corpus_accuracy",accuracy)
        figure("wer_distribution",distribution)
        figure("cer_distribution",lambda ax:distribution(ax,"cer"))
        figure("accuracy_speed",speed)
    else:
        for name in ("corpus_accuracy","wer_distribution","cer_distribution","accuracy_speed"):
            for ext in ("svg","png"):
                (directory/(name+"."+ext)).unlink(missing_ok=True)
