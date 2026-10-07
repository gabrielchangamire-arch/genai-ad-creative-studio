import React from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from './App.jsx';
import * as api from './api.js';

vi.mock('./api.js', () => ({listCampaigns: vi.fn(), getConfig: vi.fn(), generateCampaign: vi.fn(), createCampaign: vi.fn()}));
const set = n => ({headlines:[`Headline ${n}`], descriptions:[`Description ${n}`], calls_to_action:[`CTA ${n}`], campaign_concepts:[`Concept ${n}`]});
const version = n => ({version:n, created_at:'2026-01-01T00:00:00Z', creative_set:set(n), metadata:{mode:'mock', request_id:`req_${n}`, latency_ms:1, attempts:0}});
const campaign = (count=1) => ({id:'c1', product_name:'Signal Desk', target_audience:'Managers', tone:'practical', creative_set:set(count), creative_versions:Array.from({length:count}, (_,i)=>version(count-i))});
afterEach(cleanup);
beforeEach(() => { vi.resetAllMocks(); api.listCampaigns.mockResolvedValue([campaign()]); api.getConfig.mockResolvedValue({generation_mode:'mock'}); });

describe('creative version workflow', () => {
  it('labels mock mode and compares persisted versions', async () => {
    api.listCampaigns.mockResolvedValue([campaign(2)]);
    render(<App/>);
    await screen.findByText(/OFFLINE MOCK/);
    expect(screen.getByText('Headline 2')).toBeTruthy();
    await userEvent.selectOptions(screen.getByLabelText('Compare with'), '1');
    expect(screen.getByText('Headline 1')).toBeTruthy();
    await userEvent.selectOptions(screen.getByLabelText('View version'), '1');
    expect(screen.queryByText('Headline 2')).toBeNull();
  });

  it('keeps old output visible while loading and disables competing operations', async () => {
    let resolve;
    api.generateCampaign.mockReturnValue(new Promise(r=>{resolve=r}));
    render(<App/>);
    const generate=await screen.findByRole('button',{name:'Generate new version'});
    await waitFor(()=>expect(generate.disabled).toBe(false));
    await userEvent.click(generate);
    expect(screen.getByRole('button',{name:'Generating…'}).disabled).toBe(true);
    expect(screen.getByRole('button',{name:'Save campaign'}).disabled).toBe(true);
    expect(screen.getByText('Headline 1')).toBeTruthy();
    resolve(campaign(2));
    await screen.findByText('Headline 2');
    expect(screen.getByText('Headline 1')).toBeTruthy();
    expect(screen.getByLabelText('Compare with').value).toBe('1');
  });

  it('shows a retry state without dropping prior output after failure', async () => {
    api.generateCampaign.mockRejectedValueOnce(new Error('Generation failed. Previous versions are preserved.')).mockResolvedValueOnce(campaign(2));
    render(<App/>);
    await screen.findByText('Headline 1');
    await userEvent.click(screen.getByRole('button',{name:'Generate new version'}));
    await screen.findByText('Generation failed. Previous versions are preserved.');
    expect(screen.getByText('Headline 1')).toBeTruthy();
    await userEvent.click(screen.getByRole('button',{name:'Retry generation'}));
    await screen.findByText('Headline 2');
    expect(api.generateCampaign).toHaveBeenCalledTimes(2);
  });

  it('retries initial loading', async () => {
    api.listCampaigns.mockRejectedValueOnce(new Error('Network unavailable')).mockResolvedValueOnce([campaign()]);
    render(<App/>);
    await userEvent.click(await screen.findByRole('button',{name:'Retry loading campaigns'}));
    await screen.findByText('Headline 1');
    expect(screen.queryByRole('button',{name:'Retry loading campaigns'})).toBeNull();
  });

  it('labels live mode without exposing settings or credentials', async () => {
    api.getConfig.mockResolvedValue({generation_mode:'provider'});
    render(<App/>);
    expect(await screen.findByText(/LIVE PROVIDER/)).toBeTruthy();
  });
});
