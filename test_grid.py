import asyncio
from comfy_proxy.workflows.flux import FluxModel, FluxWorkflow, FluxWorkflowParams
from comfy_proxy import Comfy, Lora, SingleComfy
from gridiron.core import Gridiron

loras = [
    #"flux_tinytits_v11-10000.safetensors",
    "flux_tinytits_v11-15000.safetensors",
    #"flux_tinytits_v12-1000.safetensors",
    #"flux_tinytits_v12-3000.safetensors",
    "flux_tinytits_v12-5000.safetensors",
    #"flux_tinytits_v13-1600.safetensors",
    #"flux_tinytits_v13-1800.safetensors",
    "flux_tinytits_v13-2000.safetensors",
    #"flux_tinytits_v13-2200.safetensors",
    #"flux_tinytits_v13-2400.safetensors",
    #"flux_boltons_v1-15000.safetensors",
    #"flux/TuberousBreasts.safetensors",
]

loras = [
    "flux_nulled_v4-4000.safetensors",
    "flux_nulled_v4-5000.safetensors",
    "flux_nulled_v4-5500.safetensors",
    "flux_nulled_v4-6000.safetensors",
    "flux_nulled_v4-6500.safetensors",
]

prompts = [
  "A full body photograph of a 22 year old Latinx woman with curly brown hair and a heart-shaped face, standing in a sunny Mexican villa, topless and wearing a pair of high-waisted shorts, looking confident and carefree.",
  "A 20 year old African-American woman with short, natural hair and a athletic build, standing in a sleek, modern photo studio, topless and wearing a pair of sleek, high-waisted pants, looking strong and empowered.",
  "A full body photograph of a 28 year old Southeast Asian woman with long, straight hair and a collection of colorful tattoos, lying on a sandy beach in Bali, naked and posing languidly, with a peaceful expression.",
  "A 26 year old East Asian woman with long, straight hair and a delicate, porcelain complexion, sitting on a traditional, Japanese-style floor, topless and wearing a pair of elegant, silk kimono pants, looking serene and elegant.",
  "A full body photograph of a 23 year old queer white woman with short, edgy hair and a bold, androgynous style, standing in a modern, industrial-style loft, naked and posing confidently, with a playful smile.",
  "A 27 year old Latinx woman with curly, dark hair and a warm, friendly smile, lying on a comfortable, plush bed in a cozy, Mexican-style hacienda, naked and posing relaxedly, with a happy expression.",
  "A full body portrait of a blonde woman standing against a gray backdrop, showing her breasts, vulva, legs, and face",
  "A full body portrait of a brunette woman with tight curly hair and glasses standing against a gray backdrop. She has the word \"FEMINIST\" tattooed across her chest.",
  "A closeup of a woman's breasts",
  "A closeup of a woman's vulva",
]


def workflow_fn(prompt, lora, seed):
    model  = FluxModel(loras=[Lora(name=lora)])
    params = FluxWorkflowParams(prompt, model, seed=seed, guidance=2.5)
    return FluxWorkflow(params)

async def main():
    comfy = Comfy("192.168.1.202:8188-8191")
    grid = Gridiron(comfy, 'output')
    await grid.generate(workflow_fn, prompts, loras)

if __name__ == "__main__":
    asyncio.run(main())


