import { useEffect, useMemo, useState } from "react";
import {
  ArrowRight,
  BriefcaseBusiness,
  LoaderCircle,
  Megaphone,
  Sparkles,
} from "lucide-react";

import { createCampaign, generateCampaign, listCampaigns } from "./api.js";

const initialBrief = {
  product_name: "",
  product_description: "",
  target_audience: "",
  tone: "practical",
  objective: "",
};

const tones = ["practical", "bold", "warm", "playful", "premium"];

function App() {
  const [brief, setBrief] = useState(initialBrief);
  const [campaigns, setCampaigns] = useState([]);
  const [selectedCampaign, setSelectedCampaign] = useState(null);
  const [status, setStatus] = useState("Loading campaigns...");
  const [busyAction, setBusyAction] = useState("");

  useEffect(() => {
    let mounted = true;

    listCampaigns()
      .then((items) => {
        if (!mounted) {
          return;
        }

        setCampaigns(items);
        setSelectedCampaign(items[0] ?? null);
        setStatus(items.length ? "" : "No campaigns saved yet.");
      })
      .catch((error) => {
        if (mounted) {
          setStatus(error.message);
        }
      });

    return () => {
      mounted = false;
    };
  }, []);

  const creativeCount = useMemo(
    () => campaigns.filter((campaign) => campaign.creative_set).length,
    [campaigns],
  );

  function updateBrief(field, value) {
    setBrief((current) => ({ ...current, [field]: value }));
  }

  async function handleCreateCampaign(event) {
    event.preventDefault();
    setBusyAction("create");
    setStatus("");

    try {
      const campaign = await createCampaign(brief);
      setCampaigns((current) => [campaign, ...current]);
      setSelectedCampaign(campaign);
      setBrief(initialBrief);
    } catch (error) {
      setStatus(error.message);
    } finally {
      setBusyAction("");
    }
  }

  async function handleGenerate() {
    if (!selectedCampaign) {
      return;
    }

    setBusyAction("generate");
    setStatus("");

    try {
      const campaign = await generateCampaign(selectedCampaign.id);
      setSelectedCampaign(campaign);
      setCampaigns((current) =>
        current.map((item) => (item.id === campaign.id ? campaign : item)),
      );
    } catch (error) {
      setStatus(error.message);
    } finally {
      setBusyAction("");
    }
  }

  return (
    <main className="studio-shell">
      <header className="studio-header">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">
            <Megaphone size={22} />
          </span>
          <div>
            <p>Campaign workspace</p>
            <h1>GenAI Ad Creative Studio</h1>
          </div>
        </div>
        <div className="workspace-stats" aria-label="Campaign counts">
          <Stat label="Campaigns" value={campaigns.length} />
          <Stat label="Creative sets" value={creativeCount} />
        </div>
      </header>

      <section className="studio-grid">
        <aside className="campaign-rail">
          <div className="section-heading">
            <BriefcaseBusiness size={18} />
            <h2>Campaigns</h2>
          </div>
          <div className="campaign-list">
            {campaigns.map((campaign) => (
              <button
                className={
                  campaign.id === selectedCampaign?.id
                    ? "campaign-item is-active"
                    : "campaign-item"
                }
                key={campaign.id}
                onClick={() => setSelectedCampaign(campaign)}
                type="button"
              >
                <strong>{campaign.product_name}</strong>
                <span>{campaign.target_audience}</span>
                <em>{campaign.tone}</em>
              </button>
            ))}
          </div>
        </aside>

        <form className="brief-panel" onSubmit={handleCreateCampaign}>
          <div className="section-heading">
            <Sparkles size={18} />
            <h2>Campaign brief</h2>
          </div>
          <Field
            label="Product name"
            name="product_name"
            onChange={updateBrief}
            value={brief.product_name}
          />
          <Field
            label="Product detail"
            name="product_description"
            onChange={updateBrief}
            textarea
            value={brief.product_description}
          />
          <div className="field-row">
            <Field
              label="Target audience"
              name="target_audience"
              onChange={updateBrief}
              value={brief.target_audience}
            />
            <label className="field">
              <span>Tone</span>
              <select
                onChange={(event) => updateBrief("tone", event.target.value)}
                value={brief.tone}
              >
                {tones.map((tone) => (
                  <option key={tone} value={tone}>
                    {tone}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <Field
            label="Objective"
            name="objective"
            onChange={updateBrief}
            value={brief.objective}
          />
          <button className="primary-button" disabled={busyAction === "create"}>
            {busyAction === "create" ? (
              <LoaderCircle className="spin" size={18} />
            ) : (
              <ArrowRight size={18} />
            )}
            Save campaign
          </button>
        </form>

        <section className="creative-panel">
          <div className="creative-topline">
            <div>
              <div className="section-heading">
                <Megaphone size={18} />
                <h2>Creative set</h2>
              </div>
              <h3>{selectedCampaign?.product_name ?? "Select a campaign"}</h3>
            </div>
            <button
              className="secondary-button"
              disabled={!selectedCampaign || busyAction === "generate"}
              onClick={handleGenerate}
              type="button"
            >
              {busyAction === "generate" ? (
                <LoaderCircle className="spin" size={18} />
              ) : (
                <Sparkles size={18} />
              )}
              Generate
            </button>
          </div>

          {selectedCampaign?.creative_set ? (
            <CreativeSet creativeSet={selectedCampaign.creative_set} />
          ) : (
            <div className="empty-state">
              <strong>Creative set pending</strong>
              <span>Save a brief, then generate copy from the selected campaign.</span>
            </div>
          )}
        </section>
      </section>

      <p className={status ? "status-line" : "status-line is-hidden"}>{status}</p>
    </main>
  );
}

function CreativeSet({ creativeSet }) {
  return (
    <div className="creative-grid">
      <CreativeColumn label="Headlines" items={creativeSet.headlines} />
      <CreativeColumn label="Descriptions" items={creativeSet.descriptions} />
      <CreativeColumn label="Calls to action" items={creativeSet.calls_to_action} />
      <CreativeColumn label="Campaign concepts" items={creativeSet.campaign_concepts} />
    </div>
  );
}

function CreativeColumn({ items, label }) {
  return (
    <article className="creative-column">
      <h4>{label}</h4>
      <ul>
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </article>
  );
}

function Field({ label, name, onChange, textarea = false, value }) {
  const inputProps = {
    id: name,
    name,
    onChange: (event) => onChange(name, event.target.value),
    required: true,
    value,
  };

  return (
    <label className="field" htmlFor={name}>
      <span>{label}</span>
      {textarea ? <textarea rows="4" {...inputProps} /> : <input {...inputProps} />}
    </label>
  );
}

function Stat({ label, value }) {
  return (
    <div className="stat">
      <strong>{value}</strong>
      <span>{label}</span>
    </div>
  );
}

export default App;
