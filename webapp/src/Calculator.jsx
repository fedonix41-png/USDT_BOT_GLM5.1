import React, { useState, useEffect } from 'react';
import WebApp from '@twa-dev/sdk';
import { ArrowLeft, ArrowDownUp, Info } from 'lucide-react';
import './index.css';

export default function Calculator({ type, onBack }) {
  const [rates, setRates] = useState({ buy: 0, sell: 0 });
  const [usdtAmount, setUsdtAmount] = useState('');
  const [fiatAmount, setFiatAmount] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  // Fetch rates
  useEffect(() => {
    const fetchRates = async () => {
      try {
        // Fallback to localhost if not served from same origin
        const apiUrl = import.meta.env.VITE_API_URL || '';
        const response = await fetch(`${apiUrl}/api/v1/rates`);
        if (!response.ok) throw new Error('Failed to fetch rates');
        const data = await response.json();
        setRates(data);
      } catch (err) {
        console.error(err);
        // Mock data for UI testing if API is unreachable
        setRates({ buy: 98.50, sell: 96.20 });
      } finally {
        setIsLoading(false);
      }
    };
    fetchRates();
  }, []);

  const rate = type === 'Buy' ? rates.buy : rates.sell;
  const isBuy = type === 'Buy';

  const handleUsdtChange = (e) => {
    const val = e.target.value;
    if (val === '' || /^\d*\.?\d{0,2}$/.test(val)) {
      setUsdtAmount(val);
      if (val && rate > 0) {
        setFiatAmount((parseFloat(val) * rate).toFixed(2));
      } else {
        setFiatAmount('');
      }
      validate(val);
    }
  };

  const handleFiatChange = (e) => {
    const val = e.target.value;
    if (val === '' || /^\d*\.?\d{0,2}$/.test(val)) {
      setFiatAmount(val);
      if (val && rate > 0) {
        setUsdtAmount((parseFloat(val) / rate).toFixed(2));
      } else {
        setUsdtAmount('');
      }
      // Validate based on the computed USDT amount
      validate((parseFloat(val) / rate).toString());
    }
  };

  const validate = (amountStr) => {
    const amount = parseFloat(amountStr);
    if (!amountStr || isNaN(amount)) {
      setError('');
      return false;
    }
    if (amount < 0.01) {
      setError('Minimum amount is 0.01 USDT');
      return false;
    }
    if (amount > 100000) {
      setError('Maximum amount is 100,000 USDT');
      return false;
    }
    setError('');
    return true;
  };

  const handleSubmit = () => {
    if (!validate(usdtAmount)) return;
    WebApp.HapticFeedback.notificationOccurred('success');
    
    // We use WebApp.sendData to send the payload back to the Bot!
    // The Bot will intercept this and continue the FSM flow or create the order.
    const payload = JSON.stringify({
      action: isBuy ? 'buy_usdt' : 'sell_usdt',
      amount: parseFloat(usdtAmount)
    });
    
    WebApp.sendData(payload);
  };

  const isValid = usdtAmount && !error && parseFloat(usdtAmount) > 0;

  return (
    <div className="animate-in">
      <header style={{ marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <button 
          onClick={onBack}
          style={{ background: 'none', border: 'none', color: 'var(--text-primary)', cursor: 'pointer' }}
        >
          <ArrowLeft size={24} />
        </button>
        <h1 style={{ marginBottom: 0 }}>{type} USDT</h1>
      </header>

      <div className="glass-panel delay-1 animate-in" style={{ padding: '1.5rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1.5rem' }}>
          <span className="subtitle">Current Rate</span>
          <span style={{ fontWeight: 600, color: isBuy ? 'var(--accent-buy)' : 'var(--accent-sell)' }}>
            {isLoading ? '...' : `${rate.toFixed(2)} ₽`}
          </span>
        </div>

        {/* Input 1: USDT */}
        <div style={{ marginBottom: '1rem', position: 'relative' }}>
          <label className="subtitle" style={{ display: 'block', marginBottom: '0.5rem' }}>
            {isBuy ? 'You Receive' : 'You Send'}
          </label>
          <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
            <input 
              type="text" 
              inputMode="decimal"
              value={usdtAmount}
              onChange={handleUsdtChange}
              placeholder="0.00"
              style={{
                width: '100%',
                background: 'rgba(0,0,0,0.2)',
                border: `1px solid ${error ? 'var(--accent-sell)' : 'var(--border-color)'}`,
                borderRadius: '12px',
                padding: '1rem',
                paddingRight: '4rem',
                color: '#fff',
                fontSize: '1.25rem',
                fontWeight: 600,
                outline: 'none',
                transition: 'border-color 0.2s'
              }}
            />
            <span style={{ position: 'absolute', right: '1rem', fontWeight: 600, color: 'var(--text-secondary)' }}>USDT</span>
          </div>
        </div>

        <div style={{ display: 'flex', justifyContent: 'center', margin: '0.5rem 0' }}>
          <div style={{ background: 'var(--border-color)', padding: '0.5rem', borderRadius: '50%' }}>
            <ArrowDownUp size={16} color="var(--text-secondary)" />
          </div>
        </div>

        {/* Input 2: FIAT (RUB) */}
        <div style={{ marginBottom: '1.5rem', position: 'relative' }}>
          <label className="subtitle" style={{ display: 'block', marginBottom: '0.5rem' }}>
            {isBuy ? 'You Pay' : 'You Receive'}
          </label>
          <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
            <input 
              type="text" 
              inputMode="decimal"
              value={fiatAmount}
              onChange={handleFiatChange}
              placeholder="0.00"
              style={{
                width: '100%',
                background: 'rgba(0,0,0,0.2)',
                border: '1px solid var(--border-color)',
                borderRadius: '12px',
                padding: '1rem',
                paddingRight: '4rem',
                color: '#fff',
                fontSize: '1.25rem',
                fontWeight: 600,
                outline: 'none'
              }}
            />
            <span style={{ position: 'absolute', right: '1rem', fontWeight: 600, color: 'var(--text-secondary)' }}>RUB</span>
          </div>
        </div>

        {error && (
          <div style={{ color: 'var(--accent-sell)', fontSize: '0.875rem', display: 'flex', alignItems: 'center', gap: '0.25rem', marginBottom: '1rem' }}>
            <Info size={16} /> {error}
          </div>
        )}

        <button 
          onClick={handleSubmit}
          disabled={!isValid || isLoading}
          style={{
            width: '100%',
            padding: '1rem',
            borderRadius: '12px',
            border: 'none',
            background: isValid 
              ? (isBuy ? 'var(--accent-buy)' : 'var(--accent-sell)')
              : 'var(--border-color)',
            color: isValid ? '#fff' : 'var(--text-secondary)',
            fontSize: '1.125rem',
            fontWeight: 700,
            cursor: isValid ? 'pointer' : 'not-allowed',
            transition: 'all 0.2s',
            boxShadow: isValid ? `0 4px 12px ${isBuy ? 'var(--accent-buy-glow)' : 'var(--accent-sell-glow)'}` : 'none'
          }}
        >
          {isBuy ? 'Buy USDT' : 'Sell USDT'}
        </button>
      </div>
    </div>
  );
}
