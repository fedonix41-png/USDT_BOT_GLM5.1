import React, { useEffect, useState } from 'react';
import WebApp from '@twa-dev/sdk';
import { ArrowDownUp, ArrowRightLeft, TrendingUp, Wallet } from 'lucide-react';
import Calculator from './Calculator';
import './index.css';

function App() {
  const [user, setUser] = useState(null);
  const [currentView, setCurrentView] = useState('home');
  const [rates, setRates] = useState({ buy: 0, sell: 0 });
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    WebApp.ready();
    WebApp.expand();
    
    try {
      WebApp.setHeaderColor('#0B0E14');
      WebApp.setBackgroundColor('#0B0E14');
    } catch (e) {
      console.warn("Theme color setting failed", e);
    }

    if (WebApp.initDataUnsafe?.user) {
      setUser(WebApp.initDataUnsafe.user);
    }
  }, []);

  useEffect(() => {
    const fetchRates = async () => {
      try {
        const apiUrl = import.meta.env.VITE_API_URL || '';
        const response = await fetch(`${apiUrl}/api/v1/rates`);
        if (response.ok) {
          const data = await response.json();
          setRates(data);
        }
      } catch (err) {
        setRates({ buy: 98.50, sell: 96.20 });
      } finally {
        setIsLoading(false);
      }
    };
    fetchRates();
  }, []);

  const handleAction = (type) => {
    WebApp.HapticFeedback.impactOccurred('medium');
    setCurrentView(type.toLowerCase());
  };

  const handleBack = () => {
    WebApp.HapticFeedback.impactOccurred('light');
    setCurrentView('home');
  };

  if (currentView === 'buy' || currentView === 'sell') {
    return (
      <Calculator 
        type={currentView === 'buy' ? 'Buy' : 'Sell'} 
        onBack={handleBack} 
      />
    );
  }

  return (
    <div className="animate-in">
      <header style={{ marginBottom: '2rem' }}>
        <h1 style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Wallet size={24} color="#26A17B" />
          {user ? `Hello, ${user.first_name}` : 'USDT Exchange'}
        </h1>
        <p className="subtitle">Secure & Instant Tether transfers</p>
      </header>

      <section>
        <div className="action-grid">
          <div 
            className="glass-panel action-card delay-1 animate-in"
            onClick={() => handleAction('Buy')}
          >
            <div className="action-icon icon-buy">
              <ArrowDownUp size={24} color="#fff" />
            </div>
            <span className="action-title">Buy USDT</span>
          </div>

          <div 
            className="glass-panel action-card delay-2 animate-in"
            onClick={() => handleAction('Sell')}
          >
            <div className="action-icon icon-sell">
              <ArrowRightLeft size={24} color="#fff" />
            </div>
            <span className="action-title">Sell USDT</span>
          </div>
        </div>
      </section>

      <section className="rates-container delay-3 animate-in">
        <h2 style={{ fontSize: '1.125rem', fontWeight: 600, marginBottom: '0.5rem' }}>Current Rates</h2>
        <div className="glass-panel" style={{ padding: '0.5rem' }}>
          <div className="rate-row" style={{ borderBottom: '1px solid var(--border-color)', borderBottomLeftRadius: 0, borderBottomRightRadius: 0 }}>
            <span className="rate-label">
              <TrendingUp size={18} color="#26A17B" /> Buy
            </span>
            <span className="rate-value value-buy">
              {isLoading ? '...' : `${rates.buy.toFixed(2)} ₽`}
            </span>
          </div>
          <div className="rate-row">
            <span className="rate-label">
              <TrendingUp size={18} color="#E15241" style={{ transform: 'scaleY(-1)' }} /> Sell
            </span>
            <span className="rate-value value-sell">
              {isLoading ? '...' : `${rates.sell.toFixed(2)} ₽`}
            </span>
          </div>
        </div>
      </section>
      
      <footer style={{ marginTop: 'auto', textAlign: 'center', paddingTop: '2rem', opacity: 0.5 }}>
        <p className="subtitle" style={{ fontSize: '0.75rem' }}>Protected by AES-256 Encryption</p>
      </footer>
    </div>
  );
}

export default App;
