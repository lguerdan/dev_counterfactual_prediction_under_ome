import numpy as np
import pandas as pd
from functools import reduce


def preprocess_dataset(out_file):

    descriptive_stats = pd.read_stata('oregonhie_descriptive_vars.dta')
    state_programs = pd.read_stata('oregonhie_stateprograms_vars.dta')
    ed_visits = pd.read_stata('oregonhie_ed_vars.dta')
    survey_responses = pd.read_stata('oregonhie_inperson_vars.dta')

    descriptive_stats = descriptive_stats[['person_id', 'treatment', 'numhh_list']]

    # State program enrollments occuring prior to program notification date
    state_programs = state_programs[['person_id', 'snap_ever_prenotify07', 'snap_tot_hh_prenotify07',
                                    'tanf_ever_prenotify07', 'tanf_tot_hh_prenotify07']]
    
    pre_vars = ['person_id'] + [c for c in ed_visits.columns.tolist() if 'pre' in c]
    ed_visits = ed_visits[pre_vars]

    pre_survey_vars = ['person_id', 'phqtot_inp'] + [c for c in survey_responses.columns.tolist() if '_pre_' in c]
    survey_responses = survey_responses[pre_survey_vars]

    tables = [descriptive_stats, state_programs, ed_visits, survey_responses]

    # Filter to records from single-individual homes that ontain a depression score
    ohie_df = reduce(lambda left, right: pd.merge(left, right, on=['person_id'], how='inner'), tables)
    ohie_df = ohie_df[(ohie_df['numhh_list'] == 'signed self up') & ~ohie_df['phqtot_inp'].isna()]

    # Binarize total score to determine outcome variable. 
    # TODO: look into different thresholding options based on literature
    ohie_df['Y'] = (ohie_df['phqtot_inp'] > 15).astype(int)

    # Assign treatment variable
    ohie_df.rename(columns={'treatment': 'D'}, inplace=True)

    # Drop unneeded variables and convert to categorical
    ohie_df.drop(columns=['person_id', 'numhh_list'], inplace=True)
    cat_columns = ohie_df.select_dtypes(['category']).columns
    ohie_df[cat_columns] = ohie_df[cat_columns].apply(lambda x: x.cat.codes)

    # Remove ~10 rows that contain a missing value
    ohie_df = ohie_df.dropna()

    ohie_df.to_csv(out_file, index=False)


if __name__ == "__main__":
    preprocess_dataset('ohie_data.csv')