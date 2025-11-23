from pydantic import BaseModel, Field

# Model for the raw Pokemon data fetched from PokeAPI (Internal Contract)
class PokemonSpeciesData(BaseModel):
    # Use Field alias for Pythonic access but keep JSON key names clean
    name: str
    description: str = Field(alias="flavor_text")
    habitat: str | None
    is_legendary: bool = Field(alias="is_legendary")

# Model for the final, basic API response (Public Endpoint 1)
class PokemonResponse(BaseModel):
    name: str
    description: str
    habitat: str | None
    is_legendary: bool

# Model for the final, translated API response (Public Endpoint 2)
# We can reuse the basic response model structure for simplicity
class TranslatedPokemonResponse(PokemonResponse):
    pass