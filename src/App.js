import EncodingViewer from './components/EncodingViewer';
import './App.css';

function App() {
  return (
    <div className="App">
      <h1>Encoding Examples for "Exploring Latent
        Spaces of Tonal Music using Variational Autoencoders"</h1>
      <p>Here you can listen and explore to the encoding examples for the paper "Exploring Latent Spaces of Tonal Music using Variational Autoencoders".</p>
      <p>For more information, please visit the <a href="https://github.com/NadiaCarvalho/Latent-Tonal-Music">project page</a> or the <a href="https://aimc2023.pubpub.org/dash/pub/latent-spaces-tonal-music/overview">paper</a>.</p>
      <br></br>
      <EncodingViewer />
    </div>
  );
}

export default App;
