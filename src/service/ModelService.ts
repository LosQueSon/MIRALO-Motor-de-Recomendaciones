import {
  GenreRelationsRepository,
  UserPreferenceRepository
} from "../data/repositories/interfaces";
import { GenreSimilarityModel } from "../model/GenreSimilarityModel";
import { GenreRelationsDocument } from "../model/types";

export class ModelService {
  constructor(
    private readonly userRepository: UserPreferenceRepository,
    private readonly relationsRepository: GenreRelationsRepository,
    private readonly model: GenreSimilarityModel
  ) {}

  async train(): Promise<{ trainedUsers: number; relations: number }> {
    const users = await this.userRepository.findAll();
    this.model.train(users);
    const relations = this.model.getRelations();
    await this.relationsRepository.replaceAll(relations);

    return {
      trainedUsers: users.length,
      relations: relations.length
    };
  }

  async getGenreRelations(): Promise<GenreRelationsDocument[]> {
    if (!this.model.isTrained()) {
      const stored = await this.relationsRepository.findAll();
      if (stored.length > 0) {
        this.model.loadRelations(stored);
      }
    }

    return this.model.getRelations();
  }

  isTrained(): boolean {
    return this.model.isTrained();
  }
}

