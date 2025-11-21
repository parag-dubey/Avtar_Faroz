import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import ferozemAvatar from "@/assets/feroze-avatar.jpg";

const Landing = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-gradient-hero flex flex-col">
      {/* Header */}
      <header className="absolute top-0 right-0 p-6">
        <Button 
          variant="outline" 
          className="bg-card/80 backdrop-blur-sm border-primary/20 hover:bg-primary hover:text-primary-foreground transition-all"
          onClick={() => navigate("/auth")}
        >
          Login / Register
        </Button>
      </header>

      {/* Main Content */}
      <main className="flex-1 flex flex-col items-center justify-center px-4">
        <div className="text-center space-y-8 max-w-2xl">
          {/* Avatar */}
          <div className="relative inline-block">
            <div className="w-48 h-48 md:w-64 md:h-64 rounded-full overflow-hidden shadow-2xl ring-4 ring-primary/20 ring-offset-4 ring-offset-background">
              <img 
                src={ferozemAvatar} 
                alt="Feroze Azeez" 
                className="w-full h-full object-cover"
              />
            </div>
            {/* Glow effect */}
            <div className="absolute inset-0 rounded-full bg-primary/10 blur-3xl -z-10"></div>
          </div>

          {/* Text Content */}
          <div className="space-y-3">
            <h1 className="text-5xl md:text-6xl font-bold text-foreground">
              Feroze Azeez
            </h1>
            <p className="text-2xl md:text-3xl font-semibold text-primary">
              AI Financial Avatar
            </p>
            <p className="text-lg md:text-xl text-muted-foreground max-w-md mx-auto">
              Your intelligent financial advisor, available 24/7
            </p>
          </div>

          {/* CTA Button */}
          <Button 
            size="lg"
            className="px-12 py-6 text-lg font-semibold rounded-full shadow-xl hover:shadow-2xl transition-all hover:scale-105 bg-primary hover:bg-primary/90"
            onClick={() => navigate("/dashboard")}
          >
            Start Chat
          </Button>
        </div>
      </main>

      {/* Footer */}
      <footer className="p-6 text-center text-sm text-muted-foreground">
        <p>Powered by Advanced AI Technology</p>
      </footer>
    </div>
  );
};

export default Landing;
